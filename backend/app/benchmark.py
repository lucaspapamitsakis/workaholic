"""
Benchmark progression engine.

Rules:
1. Initial benchmark = first logged session's best set for an exercise.
2. A session is a "Success" if any set meets or exceeds the benchmark.
3. After N consecutive successes (configurable, default 3), the benchmark
   auto-increments and the user is notified.
4. Increment amounts are configurable per exercise.
"""
from datetime import date, datetime
from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import ExerciseSet, Benchmark, BenchmarkHistory
from .schemas import Notification


def determine_benchmark_type(exercise_sets: list) -> str:
    """Determine if an exercise is weight/reps, pace, or duration based."""
    has_weight_reps = any(s.weight_lbs and s.reps for s in exercise_sets)
    has_pace = any(s.duration_sec and s.distance_m for s in exercise_sets)
    has_duration_only = any(
        s.duration_sec and not s.distance_m and not (s.weight_lbs and s.reps)
        for s in exercise_sets
    )

    if has_weight_reps:
        return "weight_reps"
    elif has_pace:
        return "pace"
    elif has_duration_only:
        return "duration"
    return "weight_reps"


def get_best_set_for_session(
    sets: list, benchmark_type: str
) -> dict:
    """Find the best set in a session based on benchmark type."""
    if benchmark_type == "weight_reps":
        best = max(
            [s for s in sets if s.weight_lbs and s.reps],
            key=lambda s: s.estimated_1rm or (s.weight_lbs * (1 + s.reps / 30.0)),
            default=None,
        )
        if best:
            return {"weight": best.weight_lbs, "reps": best.reps, "1rm": best.estimated_1rm}
    elif benchmark_type == "pace":
        best = min(
            [s for s in sets if s.pace_sec_per_m and s.pace_sec_per_m > 0],
            key=lambda s: s.pace_sec_per_m,
            default=None,
        )
        if best:
            return {"pace": best.pace_sec_per_m, "duration": best.duration_sec, "distance": best.distance_m}
    elif benchmark_type == "duration":
        best = max(
            [s for s in sets if s.duration_sec],
            key=lambda s: s.duration_sec,
            default=None,
        )
        if best:
            return {"duration": best.duration_sec}

    return {}


def is_session_success(
    session_sets: list, benchmark: Benchmark
) -> bool:
    """Check if a session meets or exceeds the benchmark."""
    if benchmark.benchmark_type == "weight_reps":
        if benchmark.benchmark_weight is None or benchmark.benchmark_reps is None:
            return False
        benchmark_1rm = benchmark.benchmark_weight * (1 + benchmark.benchmark_reps / 30.0)
        for s in session_sets:
            if s.estimated_1rm and s.estimated_1rm >= benchmark_1rm:
                return True
            if s.weight_lbs and s.reps:
                if s.weight_lbs >= benchmark.benchmark_weight and s.reps >= benchmark.benchmark_reps:
                    return True
        return False

    elif benchmark.benchmark_type == "pace":
        if benchmark.benchmark_pace_sec_per_m is None:
            return False
        for s in session_sets:
            if s.pace_sec_per_m and s.pace_sec_per_m <= benchmark.benchmark_pace_sec_per_m:
                return True
        return False

    elif benchmark.benchmark_type == "duration":
        if benchmark.benchmark_duration_sec is None:
            return False
        for s in session_sets:
            if s.duration_sec and s.duration_sec >= benchmark.benchmark_duration_sec:
                return True
        return False

    return False


def initialize_benchmark(
    db: Session,
    exercise_name: str,
    first_session_sets: list,
    config: dict,
) -> Benchmark | None:
    """Create the initial benchmark from the first session's best set."""
    benchmark_type = determine_benchmark_type(first_session_sets)
    best = get_best_set_for_session(first_session_sets, benchmark_type)

    if not best:
        return None

    benchmark = Benchmark(
        exercise_name=exercise_name,
        benchmark_type=benchmark_type,
        benchmark_weight=best.get("weight"),
        benchmark_reps=best.get("reps"),
        benchmark_duration_sec=best.get("duration"),
        benchmark_pace_sec_per_m=best.get("pace"),
        increment_weight_lbs=config.get("default_weight_increment_lbs", 5.0),
        increment_reps=config.get("default_reps_increment", 2),
        increment_duration_sec=config.get("default_duration_increment_sec", 5.0),
        consecutive_successes=0,
    )
    db.add(benchmark)
    db.commit()
    db.refresh(benchmark)
    return benchmark


def evaluate_benchmarks(db: Session, config: dict) -> list[Notification]:
    """
    Evaluate all benchmarks against recent sessions.
    Called after sync to check for progressions.
    """
    notifications = []
    threshold = config.get("consolidation_threshold", 3)

    benchmarks = db.query(Benchmark).all()

    for benchmark in benchmarks:
        exercise_name = benchmark.exercise_name

        # Get all sessions for this exercise, ordered by date
        sessions_query = (
            db.query(ExerciseSet.date)
            .filter(ExerciseSet.exercise_name == exercise_name)
            .group_by(ExerciseSet.date)
            .order_by(ExerciseSet.date.desc())
        )

        # Only evaluate sessions after the last evaluation
        if benchmark.last_evaluated_date:
            sessions_query = sessions_query.filter(
                ExerciseSet.date > benchmark.last_evaluated_date
            )

        session_dates = [row[0] for row in sessions_query.all()]

        if not session_dates:
            continue

        # Evaluate each new session chronologically
        for session_date in reversed(session_dates):
            session_sets = (
                db.query(ExerciseSet)
                .filter(
                    ExerciseSet.exercise_name == exercise_name,
                    ExerciseSet.date == session_date,
                )
                .all()
            )

            success = is_session_success(session_sets, benchmark)

            if success:
                benchmark.consecutive_successes += 1
                # Mark the best set as a benchmark set
                _mark_benchmark_sets(db, session_sets, benchmark)
            else:
                benchmark.consecutive_successes = 0

            benchmark.last_evaluated_date = session_date

            # Check for consolidation
            if benchmark.consecutive_successes >= threshold:
                notification = _consolidate_benchmark(db, benchmark, config)
                if notification:
                    notifications.append(notification)

        db.commit()

    return notifications


def _mark_benchmark_sets(db: Session, session_sets: list, benchmark: Benchmark):
    """Mark which sets in a session meet the benchmark."""
    for s in session_sets:
        met = False
        if benchmark.benchmark_type == "weight_reps":
            if s.weight_lbs and s.reps:
                if benchmark.benchmark_weight and benchmark.benchmark_reps:
                    if s.weight_lbs >= benchmark.benchmark_weight and s.reps >= benchmark.benchmark_reps:
                        met = True
        elif benchmark.benchmark_type == "pace":
            if s.pace_sec_per_m and benchmark.benchmark_pace_sec_per_m:
                if s.pace_sec_per_m <= benchmark.benchmark_pace_sec_per_m:
                    met = True
        elif benchmark.benchmark_type == "duration":
            if s.duration_sec and benchmark.benchmark_duration_sec:
                if s.duration_sec >= benchmark.benchmark_duration_sec:
                    met = True
        s.is_benchmark_set = met


def _consolidate_benchmark(
    db: Session, benchmark: Benchmark, config: dict
) -> Notification | None:
    """Auto-increment the benchmark after consolidation threshold is met."""
    old_weight = benchmark.benchmark_weight
    old_reps = benchmark.benchmark_reps
    old_duration = benchmark.benchmark_duration_sec
    old_pace = benchmark.benchmark_pace_sec_per_m

    message_parts = []

    if benchmark.benchmark_type == "weight_reps":
        benchmark.benchmark_weight = (benchmark.benchmark_weight or 0) + benchmark.increment_weight_lbs
        message_parts.append(
            f"Weight: {old_weight} -> {benchmark.benchmark_weight} lbs"
        )
    elif benchmark.benchmark_type == "duration":
        benchmark.benchmark_duration_sec = (benchmark.benchmark_duration_sec or 0) + benchmark.increment_duration_sec
        message_parts.append(
            f"Duration: {old_duration}s -> {benchmark.benchmark_duration_sec}s"
        )
    elif benchmark.benchmark_type == "pace":
        if benchmark.increment_pace_sec_per_m:
            benchmark.benchmark_pace_sec_per_m = (
                (benchmark.benchmark_pace_sec_per_m or 0) - benchmark.increment_pace_sec_per_m
            )
            message_parts.append(
                f"Pace: {old_pace:.4f} -> {benchmark.benchmark_pace_sec_per_m:.4f} sec/m"
            )

    # Record history
    history = BenchmarkHistory(
        exercise_name=benchmark.exercise_name,
        old_weight=old_weight,
        old_reps=old_reps,
        old_duration_sec=old_duration,
        old_pace=old_pace,
        new_weight=benchmark.benchmark_weight,
        new_reps=benchmark.benchmark_reps,
        new_duration_sec=benchmark.benchmark_duration_sec,
        new_pace=benchmark.benchmark_pace_sec_per_m,
        reason=f"Consolidated after {config.get('consolidation_threshold', 3)} consecutive successes",
    )
    db.add(history)

    # Reset counter
    benchmark.consecutive_successes = 0

    message = f"Benchmark Consolidated for {benchmark.exercise_name}! {'; '.join(message_parts)}"

    return Notification(
        exercise_name=benchmark.exercise_name,
        message=message,
        notification_type="benchmark_consolidated",
        timestamp=datetime.utcnow(),
    )


def ensure_benchmarks_exist(db: Session, config: dict) -> list[Notification]:
    """
    Create initial benchmarks for exercises that don't have one yet.
    Uses the first session's best set.
    """
    notifications = []

    # Find exercises without benchmarks
    exercises_with_benchmarks = {
        b.exercise_name for b in db.query(Benchmark.exercise_name).all()
    }

    all_exercises = {
        row[0] for row in db.query(ExerciseSet.exercise_name).distinct().all()
    }

    for exercise_name in all_exercises - exercises_with_benchmarks:
        # Get the first session for this exercise
        first_date = (
            db.query(func.min(ExerciseSet.date))
            .filter(ExerciseSet.exercise_name == exercise_name)
            .scalar()
        )

        if not first_date:
            continue

        first_sets = (
            db.query(ExerciseSet)
            .filter(
                ExerciseSet.exercise_name == exercise_name,
                ExerciseSet.date == first_date,
            )
            .all()
        )

        benchmark = initialize_benchmark(db, exercise_name, first_sets, config)
        if benchmark:
            notifications.append(Notification(
                exercise_name=exercise_name,
                message=f"Initial benchmark created for {exercise_name}",
                notification_type="benchmark_created",
                timestamp=datetime.utcnow(),
            ))

    return notifications
