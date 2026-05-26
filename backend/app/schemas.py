from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class ExerciseSetOut(BaseModel):
    id: int
    date: date
    session_duration_min: Optional[int] = None
    workout_type: Optional[str] = None
    exercise_name: str
    primary_muscle_tag: str
    secondary_muscle_tags: Optional[list[str]] = None
    set_number: int
    weight_lbs: Optional[float] = None
    reps: Optional[int] = None
    duration_sec: Optional[float] = None
    distance_m: Optional[float] = None
    is_benchmark_set: bool = False
    volume: Optional[float] = None
    estimated_1rm: Optional[float] = None
    pace_sec_per_m: Optional[float] = None

    class Config:
        from_attributes = True


class SessionSummary(BaseModel):
    date: date
    session_duration_min: Optional[int] = None
    workout_type: Optional[str] = None
    exercises: list[str]
    total_volume: Optional[float] = None


class ExerciseSessionAggregate(BaseModel):
    date: date
    exercise_name: str
    total_sets: int
    total_volume: Optional[float] = None
    best_set_weight: Optional[float] = None
    best_set_reps: Optional[int] = None
    best_set_1rm: Optional[float] = None
    best_set_duration_sec: Optional[float] = None
    best_set_pace: Optional[float] = None
    benchmark_reached: bool = False
    set_details: list[ExerciseSetOut] = []


class BenchmarkOut(BaseModel):
    id: int
    exercise_name: str
    benchmark_type: str
    benchmark_weight: Optional[float] = None
    benchmark_reps: Optional[int] = None
    benchmark_duration_sec: Optional[float] = None
    benchmark_pace_sec_per_m: Optional[float] = None
    increment_weight_lbs: float = 5.0
    increment_reps: int = 2
    increment_duration_sec: float = 5.0
    increment_pace_sec_per_m: Optional[float] = None
    consecutive_successes: int = 0
    last_evaluated_date: Optional[date] = None

    class Config:
        from_attributes = True


class BenchmarkUpdate(BaseModel):
    increment_weight_lbs: Optional[float] = None
    increment_reps: Optional[int] = None
    increment_duration_sec: Optional[float] = None
    increment_pace_sec_per_m: Optional[float] = None


class BenchmarkHistoryOut(BaseModel):
    id: int
    exercise_name: str
    old_weight: Optional[float] = None
    old_reps: Optional[int] = None
    old_duration_sec: Optional[float] = None
    old_pace: Optional[float] = None
    new_weight: Optional[float] = None
    new_reps: Optional[int] = None
    new_duration_sec: Optional[float] = None
    new_pace: Optional[float] = None
    reason: Optional[str] = None
    consolidated_at: datetime

    class Config:
        from_attributes = True


class Notification(BaseModel):
    exercise_name: str
    message: str
    notification_type: str  # "benchmark_consolidated", "benchmark_created"
    timestamp: datetime


class SyncResult(BaseModel):
    files_scanned: int
    files_parsed: int
    sets_added: int
    errors: list[str] = []
    notifications: list[Notification] = []


class ConfigOut(BaseModel):
    obsidian_vault_path: str
    notes_subfolder: str
    visualization_session_count: int
    default_weight_increment_lbs: float
    default_reps_increment: int
    default_duration_increment_sec: float
    consolidation_threshold: int


class ConfigUpdate(BaseModel):
    obsidian_vault_path: Optional[str] = None
    notes_subfolder: Optional[str] = None
    visualization_session_count: Optional[int] = None
    default_weight_increment_lbs: Optional[float] = None
    default_reps_increment: Optional[int] = None
    default_duration_increment_sec: Optional[float] = None
    consolidation_threshold: Optional[int] = None
