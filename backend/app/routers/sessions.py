from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import ExerciseSet
from ..schemas import SessionSummary, WorkoutSummary, WorkoutTypeCount

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionSummary])
def get_recent_sessions(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent session summaries."""
    dates = (
        db.query(ExerciseSet.date)
        .group_by(ExerciseSet.date)
        .order_by(ExerciseSet.date.desc())
        .limit(limit)
        .all()
    )

    summaries = []
    for (session_date,) in dates:
        sets = (
            db.query(ExerciseSet)
            .filter(ExerciseSet.date == session_date)
            .all()
        )

        exercises = sorted(set(s.exercise_name for s in sets))
        workout_type = sets[0].workout_type if sets else None
        duration = sets[0].session_duration_min if sets else None
        total_volume = sum(s.volume or 0 for s in sets) or None

        summaries.append(SessionSummary(
            date=session_date,
            session_duration_min=duration,
            workout_type=workout_type,
            exercises=exercises,
            total_volume=total_volume,
        ))

    return summaries


@router.get("/summary", response_model=WorkoutSummary)
def get_workout_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Summarize sessions by workout type for the last `days` days.

    Each unique date counts as one session — even if multiple workout types
    were logged the same day (which shouldn't normally happen), we deduplicate
    on date+workout_type to avoid double-counting sets within a session.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    rows = (
        db.query(ExerciseSet.date, ExerciseSet.workout_type)
        .filter(ExerciseSet.date >= start_date)
        .filter(ExerciseSet.date <= end_date)
        .group_by(ExerciseSet.date, ExerciseSet.workout_type)
        .all()
    )

    counts: dict[str, int] = {}
    for _, workout_type in rows:
        label = (workout_type or "Untagged").strip()
        counts[label] = counts.get(label, 0) + 1

    by_type = sorted(
        (WorkoutTypeCount(workout_type=k, count=v) for k, v in counts.items()),
        key=lambda x: (-x.count, x.workout_type),
    )

    return WorkoutSummary(
        period_days=days,
        start_date=start_date,
        end_date=end_date,
        total_sessions=sum(counts.values()),
        by_type=by_type,
    )
