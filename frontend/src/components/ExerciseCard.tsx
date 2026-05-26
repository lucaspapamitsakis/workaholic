import { useEffect, useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { api } from "../api/client";
import type { ExerciseSessionAggregate, Benchmark } from "../api/client";
import {
  formatShortDate,
  formatPacePer500m,
  paceToMetersPerSecond,
  formatDuration,
  formatNumber,
} from "../utils/format";
import "./ExerciseCard.css";

interface Props {
  exerciseName: string;
}

type Metric = "volume" | "1rm" | "reps" | "total_reps" | "duration" | "pace";

const METRIC_LABEL: Record<Metric, string> = {
  volume: "Session Volume (lbs)",
  "1rm": "Est. 1RM (lbs)",
  reps: "Best Reps",
  total_reps: "Total Reps",
  duration: "Best Duration (sec)",
  pace: "Speed (m/s)",
};

export default function ExerciseCard({ exerciseName }: Props) {
  const [sessions, setSessions] = useState<ExerciseSessionAggregate[]>([]);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [metric, setMetric] = useState<Metric | null>(null);

  useEffect(() => {
    api.getExerciseSessions(exerciseName).then((data) => {
      // Backend returns sessions in date-DESC order. Keep that for the table
      // but build a separate chronological list for the chart.
      setSessions(data);
    });
    api.getExerciseBenchmark(exerciseName).then(setBenchmark).catch(() => {});
  }, [exerciseName]);

  /** Available metrics, derived from what the data actually contains. */
  const availableMetrics = useMemo<Metric[]>(() => {
    if (sessions.length === 0) return [];
    const m: Metric[] = [];
    if (sessions.some((s) => s.total_volume != null)) m.push("volume");
    if (sessions.some((s) => s.best_set_1rm != null)) m.push("1rm");
    if (sessions.some((s) => s.best_reps_in_session != null && s.best_set_1rm == null)) {
      m.push("reps");
      m.push("total_reps");
    }
    if (sessions.some((s) => s.best_set_duration_sec != null)) m.push("duration");
    if (sessions.some((s) => s.best_set_pace != null)) m.push("pace");
    return m;
  }, [sessions]);

  // Auto-pick a sensible default metric once the data loads.
  useEffect(() => {
    if (metric == null && availableMetrics.length > 0) {
      setMetric(availableMetrics[0]);
    }
  }, [metric, availableMetrics]);

  const chartData = useMemo(() => {
    return [...sessions]
      .reverse() // chronological for x-axis
      .map((s) => ({
        date: formatShortDate(s.date),
        volume: s.total_volume,
        "1rm": s.best_set_1rm ? Math.round(s.best_set_1rm * 10) / 10 : null,
        reps: s.best_reps_in_session,
        total_reps: s.total_reps,
        duration: s.best_set_duration_sec,
        pace: paceToMetersPerSecond(s.best_set_pace),
      }));
  }, [sessions]);

  if (sessions.length === 0) {
    return (
      <div className="card exercise-card">
        <h3>{exerciseName}</h3>
        <p className="empty-state">No session data yet.</p>
      </div>
    );
  }

  return (
    <div className="card exercise-card">
      <div className="exercise-header">
        <h3>{exerciseName}</h3>
        <div className="metric-selector">
          {availableMetrics.map((m) => (
            <button
              key={m}
              className={metric === m ? "active" : ""}
              onClick={() => setMetric(m)}
            >
              {METRIC_LABEL[m].replace(/\s*\(.+\)/, "")}
            </button>
          ))}
        </div>
      </div>

      {benchmark && (
        <div className="benchmark-display">
          <span className="benchmark-label">Benchmark:</span>
          <span className="benchmark-value">{formatBenchmark(benchmark)}</span>
          <span className="benchmark-progress">
            ({benchmark.consecutive_successes} consecutive success
            {benchmark.consecutive_successes === 1 ? "" : "es"})
          </span>
        </div>
      )}

      {metric && (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" stroke="var(--text-secondary)" fontSize={12} />
              <YAxis stroke="var(--text-secondary)" fontSize={12} />
              <Tooltip
                contentStyle={{
                  background: "var(--bg-secondary)",
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius)",
                  color: "var(--text-primary)",
                }}
                formatter={(value) => [value as number, METRIC_LABEL[metric]]}
              />
              <Line
                type="monotone"
                dataKey={metric}
                stroke="var(--accent)"
                strokeWidth={2}
                dot={{ fill: "var(--accent)", r: 4 }}
                activeDot={{ r: 6 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <table className="session-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Sets</th>
            <th>Cumulative</th>
            <th>Set Details</th>
            <th>Best Set</th>
            <th>Benchmark</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.date}>
              <td>{formatShortDate(s.date)}</td>
              <td>{s.total_sets}</td>
              <td>{cumulativeStat(s)}</td>
              <td className="set-details-cell">{formatSetDetails(s)}</td>
              <td>{bestSetText(s)}</td>
              <td>
                {s.benchmark_reached ? (
                  <span className="badge success">Reached</span>
                ) : (
                  <span className="badge warning">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatBenchmark(b: Benchmark): string {
  if (b.benchmark_type === "weight_reps") {
    return `${b.benchmark_reps} reps × ${b.benchmark_weight} lbs`;
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

function formatSetDetails(s: ExerciseSessionAggregate): string {
  return s.set_details
    .map((set) => {
      if (set.weight_lbs && set.reps) return `${set.reps}×${set.weight_lbs}`;
      if (set.duration_sec && set.distance_m)
        return `${formatDuration(set.duration_sec)}@${set.distance_m}m`;
      if (set.duration_sec) return formatDuration(set.duration_sec);
      if (set.reps) return `${set.reps} reps`;
      return "—";
    })
    .join(", ");
}

function cumulativeStat(s: ExerciseSessionAggregate): string {
  if (s.total_volume) return `${formatNumber(s.total_volume, 0)} lbs`;
  if (s.total_reps) return `${s.total_reps} reps`;
  if (s.best_set_duration_sec) return `${formatDuration(s.best_set_duration_sec)} best`;
  return "—";
}

function bestSetText(s: ExerciseSessionAggregate): string {
  if (s.best_set_weight && s.best_set_reps) {
    return `${s.best_set_reps}×${s.best_set_weight}`;
  }
  if (s.best_reps_in_session) {
    return `${s.best_reps_in_session} reps`;
  }
  if (s.best_set_duration_sec && s.best_set_pace) {
    return `${formatDuration(s.best_set_duration_sec)} (${formatPacePer500m(s.best_set_pace)})`;
  }
  if (s.best_set_duration_sec) {
    return formatDuration(s.best_set_duration_sec);
  }
  return "—";
}
