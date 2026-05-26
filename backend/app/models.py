from sqlalchemy import (
    Column, Integer, Float, String, Boolean, Date, DateTime, JSON, ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class ExerciseSet(Base):
    """One row per set performed. This is the core tidy-format table."""
    __tablename__ = "exercise_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    session_duration_min = Column(Integer, nullable=True)
    workout_type = Column(String, nullable=True)
    exercise_name = Column(String, nullable=False, index=True)
    primary_muscle_tag = Column(String, nullable=False, index=True)
    secondary_muscle_tags = Column(JSON, nullable=True)
    set_number = Column(Integer, nullable=False)
    weight_lbs = Column(Float, nullable=True)
    reps = Column(Integer, nullable=True)
    duration_sec = Column(Float, nullable=True)
    distance_m = Column(Float, nullable=True)
    is_benchmark_set = Column(Boolean, default=False)

    # Derived (computed on read, but cached for query speed)
    volume = Column(Float, nullable=True)
    estimated_1rm = Column(Float, nullable=True)
    pace_sec_per_m = Column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "date", "exercise_name", "set_number",
            name="uq_date_exercise_set"
        ),
    )


class Benchmark(Base):
    """Tracks the current benchmark target for each exercise."""
    __tablename__ = "benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exercise_name = Column(String, nullable=False, unique=True, index=True)
    benchmark_type = Column(String, nullable=False)  # "weight_reps", "pace", "duration"

    # For weight/reps exercises
    benchmark_weight = Column(Float, nullable=True)
    benchmark_reps = Column(Integer, nullable=True)

    # For duration exercises (planks, dead hangs)
    benchmark_duration_sec = Column(Float, nullable=True)

    # For pace exercises (rowing, running, biking)
    benchmark_pace_sec_per_m = Column(Float, nullable=True)

    # Configurable increments
    increment_weight_lbs = Column(Float, default=5.0)
    increment_reps = Column(Integer, default=2)
    increment_duration_sec = Column(Float, default=5.0)
    increment_pace_sec_per_m = Column(Float, nullable=True)

    # Tracking
    consecutive_successes = Column(Integer, default=0)
    last_evaluated_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BenchmarkHistory(Base):
    """Audit log of benchmark changes."""
    __tablename__ = "benchmark_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exercise_name = Column(String, nullable=False, index=True)
    old_weight = Column(Float, nullable=True)
    old_reps = Column(Integer, nullable=True)
    old_duration_sec = Column(Float, nullable=True)
    old_pace = Column(Float, nullable=True)
    new_weight = Column(Float, nullable=True)
    new_reps = Column(Integer, nullable=True)
    new_duration_sec = Column(Float, nullable=True)
    new_pace = Column(Float, nullable=True)
    reason = Column(String, nullable=True)
    consolidated_at = Column(DateTime, default=datetime.utcnow)


class SyncState(Base):
    """Tracks which files have been parsed and when."""
    __tablename__ = "sync_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, nullable=False, unique=True)
    file_hash = Column(String, nullable=False)
    last_synced_at = Column(DateTime, default=datetime.utcnow)


class AppConfig(Base):
    """Application configuration stored in DB for persistence."""
    __tablename__ = "app_config"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
