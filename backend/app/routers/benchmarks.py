from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Benchmark, BenchmarkHistory
from ..schemas import BenchmarkOut, BenchmarkUpdate, BenchmarkHistoryOut

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])


@router.get("", response_model=list[BenchmarkOut])
def get_all_benchmarks(db: Session = Depends(get_db)):
    """Get all exercise benchmarks."""
    return db.query(Benchmark).order_by(Benchmark.exercise_name).all()


@router.get("/{exercise_name}", response_model=BenchmarkOut)
def get_benchmark(exercise_name: str, db: Session = Depends(get_db)):
    """Get benchmark for a specific exercise."""
    benchmark = (
        db.query(Benchmark)
        .filter(Benchmark.exercise_name == exercise_name)
        .first()
    )
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return benchmark


@router.patch("/{exercise_name}", response_model=BenchmarkOut)
def update_benchmark_increments(
    exercise_name: str,
    update: BenchmarkUpdate,
    db: Session = Depends(get_db),
):
    """Update the increment configuration for an exercise's benchmark."""
    benchmark = (
        db.query(Benchmark)
        .filter(Benchmark.exercise_name == exercise_name)
        .first()
    )
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    if update.increment_weight_lbs is not None:
        benchmark.increment_weight_lbs = update.increment_weight_lbs
    if update.increment_reps is not None:
        benchmark.increment_reps = update.increment_reps
    if update.increment_duration_sec is not None:
        benchmark.increment_duration_sec = update.increment_duration_sec
    if update.increment_pace_sec_per_m is not None:
        benchmark.increment_pace_sec_per_m = update.increment_pace_sec_per_m

    db.commit()
    db.refresh(benchmark)
    return benchmark


@router.get("/{exercise_name}/history", response_model=list[BenchmarkHistoryOut])
def get_benchmark_history(exercise_name: str, db: Session = Depends(get_db)):
    """Get the history of benchmark changes for an exercise."""
    return (
        db.query(BenchmarkHistory)
        .filter(BenchmarkHistory.exercise_name == exercise_name)
        .order_by(BenchmarkHistory.consolidated_at.desc())
        .all()
    )
