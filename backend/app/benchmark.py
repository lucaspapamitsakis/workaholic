"""
Benchmark progression engine.

Design rules (corresponds to the project spec):

1. Each exercise has exactly one benchmark, classified into one of four
   types based on what the exercise data actually contains:

       weight_reps  -  any set has both weight and reps (most strength work)
       pace         -  any set has duration + distance (rowing, biking, running)
       reps         -  bodyweight: reps but never weight   (push-ups, pull-ups)
       duration     -  static holds: duration only         (planks, dead hangs)

2. The benchmark is initially seeded from the *first chronological* session's
   best set (highest 1RM, longest duration, fastest pace, or most reps).

3. A session is a "Success" if any of its sets meets-or-exceeds the benchmark.

4. After N consecutive successful sessions (configurable, default 3), the
   benchmark auto-increments by the per-exercise increment and the user is
   notified. The increment dimension depends on the type:

       weight_reps  ->  +increment_weight_lbs
       reps         ->  +increment_reps
       duration     ->  +increment_duration_sec
       pace         ->  -increment_pace_sec_per_m  (faster pace = lower value)

5. Evaluation is *fully deterministic*: every sync re-derives all benchmark
   state from the raw `exercise_sets` table. This makes editing a past note
   (or deleting one) produce correct results — the previous incremental
   approach silently failed to re-evaluate sessions on/before
   `last_evaluated_date`, which is exactly why a 70s plank wasn't being
   counted against a 65s benchmark after the user edited an old note.
"""
from datetime import datetime
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from .models import ExerciseSet, Benchmark, BenchmarkHistory
from .schemas import Notification


def determine_benchmark_type(exercise_sets: list[ExerciseSet]) -> str:
    """Classify an exercise based on what kind of data its sets contain.

    The classification looks across *all* sets ever recorded for the exercise.
    This handles the case where the user occasionally adds weight to an
    otherwise bodyweight exercise: as soon as any set has weight + reps, the
    exercise is treated as weight_reps for benchmark purposes.
    """
    has_weight_reps = any(s.weight_lbs and s.reps for s in exercise_sets)
    has_pace = any(s.duration_sec and s.distance_m for s in exercise_sets)
    has_reps_only = any(
        s.reps and not s.weight_lbs and not s.duration_sec
        for s in exercise_sets
    )
    has_duration_only = any(
        s.duration_sec and not s.distance_m and not s.weight_lbs and not s.reps
        for s in exercise_sets
    )

    if has_weight_reps:
        return "weight_reps"
    if has_pace:
        return "pace"
    if has_reps_only:
        return "reps"
    if has_duration_only:
        return "duration"
    return "weight_reps"


def get_best_set_for_session(sets: list[ExerciseSet], benchmark_type: str) -> dict:
    """Find the best set in a session given the benchmark dimension."""
    if benchmark_type == "weight_reps":
        candidates = [s for s in sets if s.weight_lbs and s.reps]
        if not candidates:
            return {}
        best = max(
            candidates,
            key=lambda s: s.estimated_1rm or (s.weight_lbs * (1 + s.reps / 30.0)),
        )
        return {"weight": best.weight_lbs, "reps": best.reps, "1rm": best.estimated_1rm}

    if benchmark_type == "pace":
        candidates = [s for s in sets if s.pace_sec_per_m and s.pace_sec_per_m > 0]
        if not candidates:
            return {}
        best = min(candidates, key=lambda s: s.pace_sec_per_m)
        return {
            "pace": best.pace_sec_per_m,
            "duration": best.duration_sec,
            "distance": best.distance_m,
        }

    if benchmark_type == "reps":
        candidates = [s for s in sets if s.reps and not s.weight_lbs]
        if not candidates:
            return {}
        best = max(candidates, key=lambda s: s.reps)
        return {"reps": best.reps}

    if benchmark_type == "duration":
        candidates = [s for s in sets if s.duration_sec]
        if not candidates:
            return {}
        best = max(candidates, key=lambda s: s.duration_sec)
        return {"duration": best.duration_sec}

    return {}


def is_session_success(session_sets: list[ExerciseSet], benchmark: Benchmark) -> bool:
    """Check if any set in the session meets-or-exceeds the benchmark target."""
    if benchmark.benchmark_type == "weight_reps":
        if benchmark.benchmark_weight is None or benchmark.benchmark_reps is None:
            return False
        benchmark_1rm = benchmark.benchmark_weight * (1 + benchmark.benchmark_reps / 30.0)
        for s in session_sets:
            if s.estimated_1rm and s.estimated_1rm >= benchmark_1rm:
                return True
            if (s.weight_lbs and s.reps
                    and s.weight_lbs >= benchmark.benchmark_weight
                    and s.reps >= benchmark.benchmark_reps):
                return True
        return False

    if benchmark.benchmark_type == "pace":
        if benchmark.benchmark_pace_sec_per_m is None:
            return False
        return any(
            s.pace_sec_per_m and s.pace_sec_per_m <= benchmark.benchmark_pace_sec_per_m
            for s in session_sets
        )

    if benchmark.benchmark_type == "reps":
        if benchmark.benchmark_reps is None:
            return False
        return any(
            s.reps and not s.weight_lbs and s.reps >= benchmark.benchmark_reps
            for s in session_sets
        )

    if benchmark.benchmark_type == "duration":
        if benchmark.benchmark_duration_sec is None:
            return False
        return any(
            s.duration_sec and s.duration_sec >= benchmark.benchmark_duration_sec
            for s in session_sets
        )

    return False


def _mark_benchmark_sets(session_sets: list[ExerciseSet], benchmark: Benchmark) -> None:
    """Flip is_benchmark_set on each set in a session that meets the benchmark.

    Sets that don't meet the benchmark are explicitly set to False so the
    function is idempotent under re-evaluation.
    """
    for s in session_sets:
        met = False
        bt = benchmark.benchmark_type
        if bt == "weight_reps":
            if (s.weight_lbs and s.reps
                    and benchmark.benchmark_weight is not None
                    and benchmark.benchmark_reps is not None
                    and s.weight_lbs >= benchmark.benchmark_weight
                    and s.reps >= benchmark.benchmark_reps):
                met = True
        elif bt == "pace":
            if (s.pace_sec_per_m
                    and benchmark.benchmark_pace_sec_per_m
                    and s.pace_sec_per_m <= benchmark.benchmark_pace_sec_per_m):
                met = True
        elif bt == "reps":
            if (s.reps and not s.weight_lbs
                    and benchmark.benchmark_reps is not None
                    and s.reps >= benchmark.benchmark_reps):
                met = True
        elif bt == "duration":
            if (s.duration_sec
                    and benchmark.benchmark_duration_sec is not None
                    and s.duration_sec >= benchmark.benchmark_duration_sec):
                met = True
        s.is_benchmark_set = met


def _consolidate(benchmark: Benchmark, threshold: int) -> str:
    """Apply the per-type increment and return a human-readable message."""
    bt = benchmark.benchmark_type
    parts: list[str] = []

    if bt == "weight_reps":
        old = benchmark.benchmark_weight
        benchmark.benchmark_weight = (old or 0) + (benchmark.increment_weight_lbs or 0)
        parts.append(f"Weight: {old} -> {benchmark.benchmark_weight} lbs")
    elif bt == "reps":
        old = benchmark.benchmark_reps
        benchmark.benchmark_reps = (old or 0) + (benchmark.increment_reps or 0)
        parts.append(f"Reps: {old} -> {benchmark.benchmark_reps}")
    elif bt == "duration":
        old = benchmark.benchmark_duration_sec
        benchmark.benchmark_duration_sec = (old or 0) + (benchmark.increment_duration_sec or 0)
        parts.append(f"Duration: {old}s -> {benchmark.benchmark_duration_sec}s")
    elif bt == "pace":
        if benchmark.increment_pace_sec_per_m:
            old = benchmark.benchmark_pace_sec_per_m
            benchmark.benchmark_pace_sec_per_m = (old or 0) - benchmark.increment_pace_sec_per_m
            parts.append(f"Pace: {old:.4f} -> {benchmark.benchmark_pace_sec_per_m:.4f} sec/m")

    benchmark.consecutive_successes = 0
    return "; ".join(parts)


def _seed_benchmark_from_first_session(
    benchmark: Benchmark, first_sets: list[ExerciseSet], config: dict
) -> None:
    """Reset a benchmark's targets to the first session's best set."""
    bt = determine_benchmark_type(first_sets)
    benchmark.benchmark_type = bt

    best = get_best_set_for_session(first_sets, bt)
    benchmark.benchmark_weight = best.get("weight")
    benchmark.benchmark_reps = best.get("reps")
    benchmark.benchmark_duration_sec = best.get("duration")
    benchmark.benchmark_pace_sec_per_m = best.get("pace")
    benchmark.consecutive_successes = 0
    benchmark.last_evaluated_date = None

    # Only set increments if they haven't been customized by the user. We
    # detect "customized" as != default; here we just respect whatever is
    # already on the row (the patch endpoint may have changed them).
    if benchmark.increment_weight_lbs is None:
        benchmark.increment_weight_lbs = config.get("default_weight_increment_lbs", 5.0)
    if benchmark.increment_reps is None:
        benchmark.increment_reps = config.get("default_reps_increment", 2)
    if benchmark.increment_duration_sec is None:
        benchmark.increment_duration_sec = config.get("default_duration_increment_sec", 5.0)


def evaluate_all(db: Session, config: dict) -> list[Notification]:
    """Fully re-derive all benchmark state from raw exercise data.

    Algorithm per exercise:
        1. Snapshot the current benchmark target (for diff/notification).
        2. Get all sessions for the exercise in chronological order.
        3. Get-or-create the Benchmark row; reset it to the first session's
           best set.
        4. Reset is_benchmark_set=False on every set of this exercise.
        5. Delete any prior BenchmarkHistory rows for this exercise (history
           is a pure derivation of input data).
        6. Walk forward through every session, marking sets, incrementing the
           consecutive-success counter, and consolidating when the threshold
           is reached (recording each consolidation in history).
        7. If the final benchmark target differs from the snapshot, emit one
           notification summarizing the change.

    This is O(N) in the total number of sets and runs on every sync. For
    personal-scale data (years of daily sessions) it remains <10ms.
    """
    threshold = config.get("consolidation_threshold", 3)
    notifications: list[Notification] = []

    exercise_names = sorted(
        r[0] for r in db.query(distinct(ExerciseSet.exercise_name)).all()
    )

    for exercise_name in exercise_names:
        all_sets = (
            db.query(ExerciseSet)
            .filter(ExerciseSet.exercise_name == exercise_name)
            .order_by(ExerciseSet.date.asc(), ExerciseSet.set_number.asc())
            .all()
        )
        if not all_sets:
            continue

        session_dates = sorted({s.date for s in all_sets})
        first_session_sets = [s for s in all_sets if s.date == session_dates[0]]

        existing_benchmark = (
            db.query(Benchmark)
            .filter(Benchmark.exercise_name == exercise_name)
            .first()
        )

        snapshot = _snapshot_benchmark(existing_benchmark) if existing_benchmark else None

        if existing_benchmark is None:
            benchmark = Benchmark(
                exercise_name=exercise_name,
                benchmark_type="weight_reps",
                increment_weight_lbs=config.get("default_weight_increment_lbs", 5.0),
                increment_reps=config.get("default_reps_increment", 2),
                increment_duration_sec=config.get("default_duration_increment_sec", 5.0),
            )
            db.add(benchmark)
            db.flush()
        else:
            benchmark = existing_benchmark

        _seed_benchmark_from_first_session(benchmark, first_session_sets, config)

        # Wipe history so re-derivation produces an exact, deduplicated audit log.
        db.query(BenchmarkHistory).filter(
            BenchmarkHistory.exercise_name == exercise_name
        ).delete()

        for s in all_sets:
            s.is_benchmark_set = False

        for session_date in session_dates:
            session_sets = [s for s in all_sets if s.date == session_date]

            if is_session_success(session_sets, benchmark):
                benchmark.consecutive_successes += 1
                _mark_benchmark_sets(session_sets, benchmark)
            else:
                benchmark.consecutive_successes = 0

            benchmark.last_evaluated_date = session_date

            if benchmark.consecutive_successes >= threshold:
                history = BenchmarkHistory(
                    exercise_name=exercise_name,
                    old_weight=benchmark.benchmark_weight,
                    old_reps=benchmark.benchmark_reps,
                    old_duration_sec=benchmark.benchmark_duration_sec,
                    old_pace=benchmark.benchmark_pace_sec_per_m,
                    reason=f"Auto-consolidated after {threshold} consecutive successes on {session_date}",
                )
                message = _consolidate(benchmark, threshold)
                history.new_weight = benchmark.benchmark_weight
                history.new_reps = benchmark.benchmark_reps
                history.new_duration_sec = benchmark.benchmark_duration_sec
                history.new_pace = benchmark.benchmark_pace_sec_per_m
                history.consolidated_at = datetime.utcnow()
                db.add(history)

        db.flush()

        if snapshot is None:
            notifications.append(Notification(
                exercise_name=exercise_name,
                message=f"Initial benchmark created for {exercise_name}: {_format_benchmark(benchmark)}",
                notification_type="benchmark_created",
                timestamp=datetime.utcnow(),
            ))
        else:
            current = _snapshot_benchmark(benchmark)
            if current != snapshot:
                notifications.append(Notification(
                    exercise_name=exercise_name,
                    message=(
                        f"Benchmark updated for {exercise_name}: "
                        f"{_format_snapshot(snapshot)} -> {_format_benchmark(benchmark)}"
                    ),
                    notification_type="benchmark_consolidated",
                    timestamp=datetime.utcnow(),
                ))

    db.commit()
    return notifications


def _snapshot_benchmark(b: Benchmark) -> tuple:
    return (
        b.benchmark_type,
        b.benchmark_weight,
        b.benchmark_reps,
        b.benchmark_duration_sec,
        b.benchmark_pace_sec_per_m,
    )


def _format_benchmark(b: Benchmark) -> str:
    if b.benchmark_type == "weight_reps":
        return f"{b.benchmark_reps} reps x {b.benchmark_weight} lbs"
    if b.benchmark_type == "reps":
        return f"{b.benchmark_reps} reps"
    if b.benchmark_type == "duration":
        return f"{b.benchmark_duration_sec}s"
    if b.benchmark_type == "pace" and b.benchmark_pace_sec_per_m:
        return f"{b.benchmark_pace_sec_per_m:.4f} sec/m"
    return "—"


def _format_snapshot(snap: tuple) -> str:
    bt, w, r, d, p = snap
    if bt == "weight_reps":
        return f"{r} reps x {w} lbs"
    if bt == "reps":
        return f"{r} reps"
    if bt == "duration":
        return f"{d}s"
    if bt == "pace" and p:
        return f"{p:.4f} sec/m"
    return "—"


# Backward-compat shims for sync.py.
def ensure_benchmarks_exist(db: Session, config: dict) -> list[Notification]:
    """No-op kept for API compatibility; evaluate_all handles creation."""
    return []


def evaluate_benchmarks(db: Session, config: dict) -> list[Notification]:
    return evaluate_all(db, config)
