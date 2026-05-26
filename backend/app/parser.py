"""
Parser for Obsidian markdown exercise notes.

Expected format:
- Date: MM/DD/YYYY
- Session_Duration: XX min
- Workout_Type: Push / Pull / Legs
- Exercise_name: Name Here
  - Muscle Tags: Primary / Secondary1 / Secondary2
  - [Reps]x[Weight]: 10x15, 14x25, 12x30
  - Duration @ Distance: 15m @ 2000m
"""
import re
import hashlib
from datetime import date, datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ParsedSet:
    set_number: int
    weight_lbs: Optional[float] = None
    reps: Optional[int] = None
    duration_sec: Optional[float] = None
    distance_m: Optional[float] = None


@dataclass
class ParsedExercise:
    name: str
    primary_muscle_tag: str
    secondary_muscle_tags: list[str] = field(default_factory=list)
    sets: list[ParsedSet] = field(default_factory=list)


@dataclass
class ParsedSession:
    date: date
    session_duration_min: Optional[int] = None
    workout_type: Optional[str] = None
    exercises: list[ParsedExercise] = field(default_factory=list)


def file_hash(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def parse_duration_string(s: str) -> float:
    """Parse a duration string into seconds.
    Supports: '60s', '1m', '15m', '1.5m', '90', '1m30s'
    """
    s = s.strip().lower()

    # Match compound like "1m30s"
    compound = re.match(r"(\d+(?:\.\d+)?)m\s*(\d+(?:\.\d+)?)s", s)
    if compound:
        return float(compound.group(1)) * 60 + float(compound.group(2))

    # Match minutes like "15m"
    m_match = re.match(r"(\d+(?:\.\d+)?)m$", s)
    if m_match:
        return float(m_match.group(1)) * 60

    # Match seconds like "60s"
    s_match = re.match(r"(\d+(?:\.\d+)?)s$", s)
    if s_match:
        return float(s_match.group(1))

    # Plain number treated as seconds
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_distance_string(s: str) -> float:
    """Parse a distance string into meters.
    Supports: '2000m', '2km', '1.5mi', '2000'
    """
    s = s.strip().lower()

    km_match = re.match(r"(\d+(?:\.\d+)?)km$", s)
    if km_match:
        return float(km_match.group(1)) * 1000

    mi_match = re.match(r"(\d+(?:\.\d+)?)mi$", s)
    if mi_match:
        return float(mi_match.group(1)) * 1609.34

    m_match = re.match(r"(\d+(?:\.\d+)?)m$", s)
    if m_match:
        return float(m_match.group(1))

    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_reps_weight(raw: str) -> list[ParsedSet]:
    """Parse '[Reps]x[Weight]' entries like '10x15, 14x25, 12x30'.
    Also handles weighted duration like '60sx30' (60 seconds at 30 lbs).
    """
    raw = raw.strip()
    if not raw or raw.lower() == "n/a":
        return []

    sets = []
    parts = [p.strip() for p in raw.split(",")]

    for i, part in enumerate(parts):
        if not part:
            continue

        # Check for duration x weight pattern (e.g., "60sx30")
        dur_weight = re.match(r"(\d+(?:\.\d+)?)s\s*x\s*(\d+(?:\.\d+)?)", part, re.IGNORECASE)
        if dur_weight:
            sets.append(ParsedSet(
                set_number=i + 1,
                duration_sec=float(dur_weight.group(1)),
                weight_lbs=float(dur_weight.group(2)),
            ))
            continue

        # Standard reps x weight (e.g., "10x15")
        rw = re.match(r"(\d+)\s*x\s*(\d+(?:\.\d+)?)", part, re.IGNORECASE)
        if rw:
            sets.append(ParsedSet(
                set_number=i + 1,
                reps=int(rw.group(1)),
                weight_lbs=float(rw.group(2)),
            ))
            continue

        # Reps only (e.g., "10" with no weight — bodyweight exercise)
        reps_only = re.match(r"^(\d+)$", part)
        if reps_only:
            sets.append(ParsedSet(
                set_number=i + 1,
                reps=int(reps_only.group(1)),
            ))

    return sets


def parse_duration_distance(raw: str) -> list[ParsedSet]:
    """Parse 'Duration @ Distance' entries.
    Examples:
      - '15m @ 2000m' -> duration=900s, distance=2000m
      - '60s, 65s, 75s' -> three sets with durations only (static hold)
      - 'N/A' -> empty
    """
    raw = raw.strip()
    if not raw or raw.lower() == "n/a":
        return []

    sets = []

    # Check if there's an @ sign (duration @ distance pattern)
    if "@" in raw:
        entries = [e.strip() for e in raw.split(",")]
        for i, entry in enumerate(entries):
            if "@" in entry:
                dur_part, dist_part = entry.split("@", 1)
                sets.append(ParsedSet(
                    set_number=i + 1,
                    duration_sec=parse_duration_string(dur_part),
                    distance_m=parse_distance_string(dist_part),
                ))
            else:
                sets.append(ParsedSet(
                    set_number=i + 1,
                    duration_sec=parse_duration_string(entry),
                ))
    else:
        # No @ sign — static duration exercise (plank, dead hang)
        entries = [e.strip() for e in raw.split(",")]
        for i, entry in enumerate(entries):
            if entry and entry.lower() != "n/a":
                sets.append(ParsedSet(
                    set_number=i + 1,
                    duration_sec=parse_duration_string(entry),
                ))

    return sets


def parse_markdown_note(content: str) -> Optional[ParsedSession]:
    """Parse a full Obsidian markdown note into a ParsedSession."""
    lines = content.split("\n")

    session_date = None
    session_duration = None
    workout_type = None
    exercises: list[ParsedExercise] = []
    current_exercise: Optional[ParsedExercise] = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Remove markdown bullet prefixes
        clean = re.sub(r"^[-*●○]\s*", "", stripped)

        # Parse session-level metadata
        date_match = re.match(r"Date:\s*(.+)", clean, re.IGNORECASE)
        if date_match:
            raw_date = date_match.group(1).strip()
            try:
                session_date = datetime.strptime(raw_date, "%m/%d/%Y").date()
            except ValueError:
                try:
                    session_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
                except ValueError:
                    pass
            continue

        dur_match = re.match(r"Session_Duration:\s*(\d+)\s*min", clean, re.IGNORECASE)
        if dur_match:
            session_duration = int(dur_match.group(1))
            continue

        type_match = re.match(r"Workout_Type:\s*(.+)", clean, re.IGNORECASE)
        if type_match:
            workout_type = type_match.group(1).strip()
            continue

        # Parse exercise name
        ex_match = re.match(r"Exercise[_ ]?name:\s*(.+)", clean, re.IGNORECASE)
        if ex_match:
            if current_exercise and current_exercise.sets:
                exercises.append(current_exercise)
            current_exercise = ParsedExercise(
                name=ex_match.group(1).strip(),
                primary_muscle_tag="",
            )
            continue

        # If we're inside an exercise block, parse its fields
        if current_exercise is not None:
            tag_match = re.match(r"Muscle\s*Tags?:\s*(.+)", clean, re.IGNORECASE)
            if tag_match:
                tags = [t.strip() for t in tag_match.group(1).split("/") if t.strip()]
                if tags:
                    current_exercise.primary_muscle_tag = tags[0]
                    current_exercise.secondary_muscle_tags = tags[1:] if len(tags) > 1 else []
                continue

            rw_match = re.match(r"\[?Reps\]?\s*x\s*\[?Weight\]?:\s*(.+)", clean, re.IGNORECASE)
            if rw_match:
                rw_sets = parse_reps_weight(rw_match.group(1))
                if rw_sets:
                    current_exercise.sets.extend(rw_sets)
                continue

            dd_match = re.match(r"Duration\s*@\s*Distance:\s*(.+)", clean, re.IGNORECASE)
            if dd_match:
                dd_sets = parse_duration_distance(dd_match.group(1))
                if dd_sets:
                    # If we already have sets from reps/weight, merge duration info
                    # Otherwise add as new sets
                    if current_exercise.sets and not dd_sets[0].reps:
                        # Extend set numbers
                        offset = len(current_exercise.sets)
                        for s in dd_sets:
                            s.set_number += offset
                    current_exercise.sets.extend(dd_sets)
                continue

    # Don't forget the last exercise
    if current_exercise and current_exercise.sets:
        exercises.append(current_exercise)

    if session_date is None:
        return None

    return ParsedSession(
        date=session_date,
        session_duration_min=session_duration,
        workout_type=workout_type,
        exercises=exercises,
    )


def compute_derived_stats(s: ParsedSet) -> dict:
    """Compute volume, estimated 1RM, and pace for a set."""
    volume = None
    estimated_1rm = None
    pace = None

    if s.weight_lbs and s.reps:
        volume = s.weight_lbs * s.reps
        # Epley formula
        if s.reps > 1:
            estimated_1rm = s.weight_lbs * (1 + s.reps / 30.0)
        else:
            estimated_1rm = s.weight_lbs

    if s.duration_sec and s.distance_m and s.distance_m > 0:
        pace = s.duration_sec / s.distance_m

    return {
        "volume": volume,
        "estimated_1rm": estimated_1rm,
        "pace_sec_per_m": pace,
    }
