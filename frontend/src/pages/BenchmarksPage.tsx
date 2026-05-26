import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { Benchmark, BenchmarkHistory } from "../api/client";
import {
  formatShortDate,
  formatPacePer500m,
  formatDuration,
} from "../utils/format";
import "./BenchmarksPage.css";

type FilterType = "all" | "weight_reps" | "reps" | "duration" | "pace";

export default function BenchmarksPage() {
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [historyByExercise, setHistoryByExercise] = useState<Record<string, BenchmarkHistory[]>>({});
  const [loadingHistoryFor, setLoadingHistoryFor] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>("all");
  const [sortBy, setSortBy] = useState<"name" | "type" | "progress">("name");

  useEffect(() => {
    api.getAllBenchmarks().then(setBenchmarks).catch(() => setBenchmarks([]));
  }, []);

  const filteredAndSorted = useMemo(() => {
    let list = filter === "all"
      ? benchmarks
      : benchmarks.filter((b) => b.benchmark_type === filter);
    list = [...list];
    if (sortBy === "name") {
      list.sort((a, b) => a.exercise_name.localeCompare(b.exercise_name));
    } else if (sortBy === "type") {
      list.sort((a, b) =>
        a.benchmark_type.localeCompare(b.benchmark_type) ||
        a.exercise_name.localeCompare(b.exercise_name)
      );
    } else if (sortBy === "progress") {
      list.sort((a, b) => b.consecutive_successes - a.consecutive_successes);
    }
    return list;
  }, [benchmarks, filter, sortBy]);

  const toggleExpand = async (exerciseName: string) => {
    if (expanded === exerciseName) {
      setExpanded(null);
      return;
    }
    setExpanded(exerciseName);
    if (!historyByExercise[exerciseName]) {
      setLoadingHistoryFor(exerciseName);
      try {
        const history = await api.getBenchmarkHistory(exerciseName);
        setHistoryByExercise((prev) => ({ ...prev, [exerciseName]: history }));
      } catch {
        setHistoryByExercise((prev) => ({ ...prev, [exerciseName]: [] }));
      } finally {
        setLoadingHistoryFor(null);
      }
    }
  };

  return (
    <div className="benchmarks-page">
      <h2>Benchmarks</h2>
      <p className="subtitle">
        Current target for every tracked exercise. Click a row to see the
        progression history.
      </p>

      <div className="benchmarks-controls">
        <div className="control-group">
          <label>Type</label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as FilterType)}
          >
            <option value="all">All</option>
            <option value="weight_reps">Weight × Reps</option>
            <option value="reps">Reps (bodyweight)</option>
            <option value="duration">Duration</option>
            <option value="pace">Pace</option>
          </select>
        </div>
        <div className="control-group">
          <label>Sort</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
          >
            <option value="name">By name</option>
            <option value="type">By type</option>
            <option value="progress">By streak (descending)</option>
          </select>
        </div>
      </div>

      {filteredAndSorted.length === 0 ? (
        <p className="empty-state">
          No benchmarks yet. Sync your notes from the Dashboard to start tracking.
        </p>
      ) : (
        <ul className="benchmarks-list">
          {filteredAndSorted.map((b) => {
            const open = expanded === b.exercise_name;
            const history = historyByExercise[b.exercise_name];
            return (
              <li key={b.exercise_name} className={`card benchmark-row ${open ? "open" : ""}`}>
                <button
                  className="benchmark-row-header"
                  onClick={() => toggleExpand(b.exercise_name)}
                >
                  <div className="benchmark-row-main">
                    <span className="benchmark-row-name">{b.exercise_name}</span>
                    <span className={`type-badge type-${b.benchmark_type}`}>
                      {typeLabel(b.benchmark_type)}
                    </span>
                  </div>
                  <div className="benchmark-row-stats">
                    <span className="target-value">{formatTarget(b)}</span>
                    <span className="streak-pill">
                      {b.consecutive_successes}/3 streak
                    </span>
                    <span className="caret">{open ? "▴" : "▾"}</span>
                  </div>
                </button>

                {open && (
                  <div className="benchmark-row-detail">
                    <div className="detail-row">
                      <strong>Increment per consolidation:</strong>{" "}
                      {formatIncrement(b)}
                    </div>
                    {b.last_evaluated_date && (
                      <div className="detail-row">
                        <strong>Last evaluated:</strong>{" "}
                        {formatShortDate(b.last_evaluated_date)}
                      </div>
                    )}
                    <div className="detail-history">
                      <strong>Progression history</strong>
                      {loadingHistoryFor === b.exercise_name ? (
                        <p className="muted">Loading…</p>
                      ) : !history || history.length === 0 ? (
                        <p className="muted">
                          No consolidations yet. The benchmark will auto-bump
                          after 3 consecutive successful sessions.
                        </p>
                      ) : (
                        <ol className="history-timeline">
                          {[...history].reverse().map((h) => (
                            <li key={h.id}>
                              <span className="history-date">
                                {formatShortDate(h.consolidated_at.slice(0, 10))}
                              </span>
                              <span className="history-change">
                                {formatHistoryDelta(b, h)}
                              </span>
                            </li>
                          ))}
                        </ol>
                      )}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function typeLabel(t: string): string {
  switch (t) {
    case "weight_reps":
      return "Weight × Reps";
    case "reps":
      return "Reps";
    case "duration":
      return "Duration";
    case "pace":
      return "Pace";
    default:
      return t;
  }
}

function formatTarget(b: Benchmark): string {
  if (b.benchmark_type === "weight_reps") {
    return `${b.benchmark_reps} × ${b.benchmark_weight} lbs`;
  }
  if (b.benchmark_type === "reps") {
    return `${b.benchmark_reps} reps`;
  }
  if (b.benchmark_type === "duration") {
    return formatDuration(b.benchmark_duration_sec);
  }
  if (b.benchmark_type === "pace") {
    return formatPacePer500m(b.benchmark_pace_sec_per_m);
  }
  return "—";
}

function formatIncrement(b: Benchmark): string {
  if (b.benchmark_type === "weight_reps") {
    return `+${b.increment_weight_lbs} lbs / +${b.increment_reps} reps`;
  }
  if (b.benchmark_type === "reps") {
    return `+${b.increment_reps} reps`;
  }
  if (b.benchmark_type === "duration") {
    return `+${b.increment_duration_sec}s`;
  }
  if (b.benchmark_type === "pace" && b.increment_pace_sec_per_m) {
    return `−${(b.increment_pace_sec_per_m * 500).toFixed(2)} sec/500m`;
  }
  return "—";
}

function formatHistoryDelta(b: Benchmark, h: BenchmarkHistory): string {
  if (b.benchmark_type === "weight_reps") {
    return `${h.old_reps ?? "?"} × ${h.old_weight ?? "?"} lbs → ${h.new_reps ?? "?"} × ${h.new_weight ?? "?"} lbs`;
  }
  if (b.benchmark_type === "reps") {
    return `${h.old_reps ?? "?"} reps → ${h.new_reps ?? "?"} reps`;
  }
  if (b.benchmark_type === "duration") {
    return `${formatDuration(h.old_duration_sec)} → ${formatDuration(h.new_duration_sec)}`;
  }
  if (b.benchmark_type === "pace") {
    return `${formatPacePer500m(h.old_pace)} → ${formatPacePer500m(h.new_pace)}`;
  }
  return "—";
}
