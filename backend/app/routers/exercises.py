from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from datetime import date
from typing import Optional

from ..database import get_db
from ..models import ExerciseSet, Benchmark
from ..schemas import ExerciseSetOut, ExerciseSessionAggregate, BenchmarkOut
from ..config import load_config

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("/muscle-groups", response_model=list[str])
def get_muscle_groups(db: Session = Depends(get_db)):
    """Get all distinct primary muscle tags."""
    results = (
        db.query(distinct(ExerciseSet.primary_muscle_tag))
        .filter(ExerciseSet.primary_muscle_tag.isnot(None))
        .all()
    )
    return sorted([r[0] for r in results if r[0]])


@router.get("/by-muscle/{muscle_tag}", response_model=list[str])
def get_exercises_for_muscle(muscle_tag: str, db: Session = Depends(get_db)):
    """Get all exercise names for a given muscle tag."""
    results = (
        db.query(distinct(ExerciseSet.exercise_name))
        .filter(ExerciseSet.primary_muscle_tag == muscle_tag)
        .all()
    )
    return sorted([r[0] for r in results])


@router.get("/{exercise_name}/sessions", response_model=list[ExerciseSessionAggregate])
def get_exercise_sessions(
    exercise_name: str,
    limit: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Get session-level aggregates for an exercise (most recent first)."""
    config = load_config()
    if limit is None:
        limit = config.get("visualization_session_count", 4)

    # Get distinct dates for this exercise
    session_dates = (
        db.query(ExerciseSet.date)
        .filter(ExerciseSet.exercise_name == exercise_name)
        .group_by(ExerciseSet.date)
        .order_by(ExerciseSet.date.desc())
        .limit(limit)
        .all()
    )

    aggregates = []
    for (session_date,) in session_dates:
        sets = (
            db.query(ExerciseSet)
            .filter(
                ExerciseSet.exercise_name == exercise_name,
                ExerciseSet.date == session_date,
            )
            .order_by(ExerciseSet.set_number)
            .all()
        )

        total_volume = sum(s.volume or 0 for s in sets) or None
        # Bodyweight-only sets (reps with no weight). Summing reps across
        # weighted sets too would double-count effort already in total_volume.
        bodyweight_reps_sum = sum(
            s.reps or 0 for s in sets if s.reps and not s.weight_lbs
        )
        total_reps = bodyweight_reps_sum or None

        best_1rm_set = max(
            [s for s in sets if s.estimated_1rm],
            key=lambda s: s.estimated_1rm,
            default=None,
        )
        best_duration_set = max(
            [s for s in sets if s.duration_sec],
            key=lambda s: s.duration_sec,
            default=None,
        )
        best_pace_set = min(
            [s for s in sets if s.pace_sec_per_m and s.pace_sec_per_m > 0],
            key=lambda s: s.pace_sec_per_m,
            default=None,
        )
        # Best single-set reps across any set (used for bodyweight exercises
        # where there is no meaningful 1RM).
        best_reps_set = max(
            [s for s in sets if s.reps],
            key=lambda s: s.reps,
            default=None,
        )

        benchmark_reached = any(s.is_benchmark_set for s in sets)
        set_details = [ExerciseSetOut.model_validate(s) for s in sets]

        aggregates.append(ExerciseSessionAggregate(
            date=session_date,
            exercise_name=exercise_name,
            total_sets=len(sets),
            total_volume=total_volume,
            total_reps=total_reps,
            best_set_weight=best_1rm_set.weight_lbs if best_1rm_set else None,
            best_set_reps=best_1rm_set.reps if best_1rm_set else None,
            best_set_1rm=best_1rm_set.estimated_1rm if best_1rm_set else None,
            best_set_duration_sec=best_duration_set.duration_sec if best_duration_set else None,
            best_set_pace=best_pace_set.pace_sec_per_m if best_pace_set else None,
            best_reps_in_session=best_reps_set.reps if best_reps_set else None,
            benchmark_reached=benchmark_reached,
            set_details=set_details,
        ))

    return aggregates


@router.get("/{exercise_name}/benchmark", response_model=Optional[BenchmarkOut])
def get_exercise_benchmark(exercise_name: str, db: Session = Depends(get_db)):
    """Get the current benchmark for an exercise."""
    benchmark = (
        db.query(Benchmark)
        .filter(Benchmark.exercise_name == exercise_name)
        .first()
    )
    if not benchmark:
        return None
    return benchmark
