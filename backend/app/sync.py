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
    """Find all markdown files in the vault/subfolder."""
    base = Path(vault_path)
    if subfolder:
        base = base / subfolder

    if not base.exists():
        return []

    return sorted(base.glob("*.md"))


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

    for filepath in note_files:
        filepath_str = str(filepath)
        current_hash = file_hash(filepath_str)

        # Check if already synced with same hash
        existing = (
            db.query(SyncState)
            .filter(SyncState.file_path == filepath_str)
            .first()
        )
        if existing and existing.file_hash == current_hash:
            continue

        # Parse the file
        try:
            content = filepath.read_text(encoding="utf-8")
            session = parse_markdown_note(content)

            if session is None:
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
    )
