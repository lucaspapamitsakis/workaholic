from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import distinct, func
from typing import Optional

from ..database import get_db
from ..models import ExerciseSet
from ..schemas import SessionSummary

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
