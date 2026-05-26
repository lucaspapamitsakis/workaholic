"""
Sync service: scans Obsidian vault for markdown notes,
parses them, and inserts data into the database.
"""
import os
from pathlib import Path
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .models import ExerciseSet, SyncState
from .parser import parse_markdown_note, compute_derived_stats, file_hash
from .benchmark import ensure_benchmarks_exist, evaluate_benchmarks
from .schemas import SyncResult, Notification


def get_note_files(vault_path: str, subfolder: str = "") -> list[Path]:
    """Find all markdown files in the vault/subfolder, recursively.

    Supports an Obsidian layout where daily notes are grouped under
    sub-folders such as Push/, Pull/, Legs/ within the configured root.
    Ignores anything inside hidden folders (e.g. `.obsidian`, `.trash`),
    EXCEPT we still want to surface iCloud `.icloud` placeholder files
    to the caller via `find_undownloaded_icloud_files`.
    """
    base = Path(vault_path).expanduser()
    if subfolder:
        base = base / subfolder

    if not base.exists():
        return []

    def _is_hidden(path: Path) -> bool:
        try:
            rel = path.relative_to(base)
        except ValueError:
            return False
        # A file inside a hidden directory should be ignored.
        return any(part.startswith(".") for part in rel.parts[:-1])

    return sorted(p for p in base.rglob("*.md") if not _is_hidden(p))


def find_undownloaded_icloud_files(vault_path: str, subfolder: str = "") -> list[Path]:
    """Return any iCloud placeholder stubs that look like undownloaded .md notes.

    macOS represents an iCloud file that has not yet been downloaded to local
    storage as `.<original_filename>.icloud`. The Documents Provider materializes
    the real file only on access (or when the user opts in via Finder). Until
    then, our `*.md` glob will silently miss those notes, which is a major
    source of "my notes aren't showing up" confusion.
    """
    base = Path(vault_path).expanduser()
    if subfolder:
        base = base / subfolder
    if not base.exists():
        return []

    placeholders: list[Path] = []
    for p in base.rglob("*.icloud"):
        # Match `.foo.md.icloud` style stubs that correspond to an .md note.
        name = p.name
        if name.startswith(".") and name.endswith(".icloud") and ".md" in name:
            placeholders.append(p)
    return placeholders


def sync_notes(db: Session, config: dict) -> SyncResult:
    """
    Main sync entrypoint. Scans for new/modified notes,
    parses them, inserts sets, then evaluates benchmarks.
    """
    vault_path = config.get("obsidian_vault_path", "")
    subfolder = config.get("notes_subfolder", "")

    if not vault_path:
        return SyncResult(
            files_scanned=0,
            files_parsed=0,
            sets_added=0,
            errors=["No Obsidian vault path configured."],
        )

    note_files = get_note_files(vault_path, subfolder)
    files_scanned = len(note_files)
    files_parsed = 0
    sets_added = 0
    errors: list[str] = []
    notifications: list[Notification] = []
    scanned_paths = [str(p) for p in note_files]
    skipped_paths: list[str] = []

    base_check = Path(vault_path).expanduser()
    if subfolder:
        base_check = base_check / subfolder
    if not base_check.exists():
        errors.append(f"Configured notes folder does not exist: {base_check}")

    if files_scanned == 0 and base_check.exists():
        errors.append(
            f"No .md files found under {base_check}. "
            "Check that your daily notes are in this folder or a subfolder of it."
        )

    placeholders = find_undownloaded_icloud_files(vault_path, subfolder)
    if placeholders:
        sample = ", ".join(p.name for p in placeholders[:3])
        more = f" (+{len(placeholders) - 3} more)" if len(placeholders) > 3 else ""
        errors.append(
            f"{len(placeholders)} iCloud file(s) are not downloaded locally and "
            f"were not scanned: {sample}{more}. "
            "Open the Obsidian folder in Finder, right-click the affected files, "
            "and choose 'Download Now' — or open them once in Obsidian — then "
            "re-run sync."
        )

    for filepath in note_files:
        filepath_str = str(filepath)
        current_hash = file_hash(filepath_str)

        existing = (
            db.query(SyncState)
            .filter(SyncState.file_path == filepath_str)
            .first()
        )
        if existing and existing.file_hash == current_hash:
            skipped_paths.append(filepath_str)
            continue

        try:
            content = filepath.read_text(encoding="utf-8")
            session = parse_markdown_note(content)

            if session is None:
                errors.append(
                    f"{filepath.name}: skipped (no Date field found — make sure the note "
                    "starts with '- Date: MM/DD/YYYY')."
                )
                skipped_paths.append(filepath_str)
                continue

            files_parsed += 1

            # If file was previously synced (modified), remove old data for that date
            if existing:
                db.query(ExerciseSet).filter(
                    ExerciseSet.date == session.date
                ).delete()

            # Insert sets
            for exercise in session.exercises:
                for s in exercise.sets:
                    derived = compute_derived_stats(s)

                    exercise_set = ExerciseSet(
                        date=session.date,
                        session_duration_min=session.session_duration_min,
                        workout_type=session.workout_type,
                        exercise_name=exercise.name,
                        primary_muscle_tag=exercise.primary_muscle_tag,
                        secondary_muscle_tags=exercise.secondary_muscle_tags or [],
                        set_number=s.set_number,
                        weight_lbs=s.weight_lbs,
                        reps=s.reps,
                        duration_sec=s.duration_sec,
                        distance_m=s.distance_m,
                        is_benchmark_set=False,
                        volume=derived["volume"],
                        estimated_1rm=derived["estimated_1rm"],
                        pace_sec_per_m=derived["pace_sec_per_m"],
                    )
                    db.add(exercise_set)
                    sets_added += 1

            # Update sync state
            if existing:
                existing.file_hash = current_hash
                existing.last_synced_at = datetime.utcnow()
            else:
                db.add(SyncState(
                    file_path=filepath_str,
                    file_hash=current_hash,
                    last_synced_at=datetime.utcnow(),
                ))

            db.commit()

        except Exception as e:
            errors.append(f"Error parsing {filepath.name}: {str(e)}")
            db.rollback()

    # After all files are synced, ensure benchmarks exist and evaluate
    try:
        benchmark_notifications = ensure_benchmarks_exist(db, config)
        notifications.extend(benchmark_notifications)

        eval_notifications = evaluate_benchmarks(db, config)
        notifications.extend(eval_notifications)

        db.commit()
    except Exception as e:
        errors.append(f"Benchmark evaluation error: {str(e)}")
        db.rollback()

    return SyncResult(
        files_scanned=files_scanned,
        files_parsed=files_parsed,
        sets_added=sets_added,
        errors=errors,
        notifications=notifications,
        scanned_paths=scanned_paths,
        skipped_paths=skipped_paths,
    )
