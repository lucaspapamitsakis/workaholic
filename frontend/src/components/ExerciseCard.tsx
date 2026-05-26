import { useEffect, useState } from "react";
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
import "./ExerciseCard.css";

interface Props {
  exerciseName: string;
}

export default function ExerciseCard({ exerciseName }: Props) {
  const [sessions, setSessions] = useState<ExerciseSessionAggregate[]>([]);
  const [benchmark, setBenchmark] = useState<Benchmark | null>(null);
  const [metric, setMetric] = useState<"volume" | "1rm" | "duration" | "pace">("volume");

  useEffect(() => {
    api.getExerciseSessions(exerciseName).then((data) => {
      setSessions(data.reverse()); // chronological order for chart
      // Auto-select best metric
      if (data.length > 0) {
        const first = data[0];
        if (first.total_volume) setMetric("volume");
        else if (first.best_set_duration_sec && first.best_set_pace) setMetric("pace");
        else if (first.best_set_duration_sec) setMetric("duration");
      }
    });
    api.getExerciseBenchmark(exerciseName).then(setBenchmark).catch(() => {});
  }, [exerciseName]);

  const chartData = sessions.map((s) => ({
    date: new Date(s.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    volume: s.total_volume,
    "1rm": s.best_set_1rm ? Math.round(s.best_set_1rm * 10) / 10 : null,
    duration: s.best_set_duration_sec,
    pace: s.best_set_pace ? Math.round((1 / s.best_set_pace) * 1000 * 100) / 100 : null,
  }));

  const formatBenchmark = () => {
    if (!benchmark) return null;
    if (benchmark.benchmark_type === "weight_reps") {
      return `${benchmark.benchmark_reps} reps × ${benchmark.benchmark_weight} lbs`;
    }
    if (benchmark.benchmark_type === "duration") {
      return `${benchmark.benchmark_duration_sec}s`;
    }
    if (benchmark.benchmark_type === "pace" && benchmark.benchmark_pace_sec_per_m) {
      return `${(benchmark.benchmark_pace_sec_per_m * 1000).toFixed(1)} sec/km`;
    }
    return null;
  };

  const formatSetDetails = (s: ExerciseSessionAggregate) => {
    return s.set_details
      .map((set) => {
        if (set.weight_lbs && set.reps) return `${set.reps}×${set.weight_lbs}`;
        if (set.duration_sec && set.distance_m)
          return `${set.duration_sec}s@${set.distance_m}m`;
        if (set.duration_sec) return `${set.duration_sec}s`;
        if (set.reps) return `${set.reps} reps`;
        return "—";
      })
      .join(", ");
  };

  const getBestSet = (s: ExerciseSessionAggregate) => {
    if (s.best_set_weight && s.best_set_reps)
      return `${s.best_set_reps}×${s.best_set_weight}`;
    if (s.best_set_duration_sec && s.best_set_pace)
      return `${s.best_set_duration_sec}s (${((1 / s.best_set_pace) * 1000).toFixed(1)} m/s)`;
    if (s.best_set_duration_sec) return `${s.best_set_duration_sec}s`;
    return "—";
  };

  const getCumulativeStat = (s: ExerciseSessionAggregate) => {
    if (s.total_volume) return `${s.total_volume.toLocaleString()} lbs`;
    if (s.best_set_duration_sec) return `${s.best_set_duration_sec}s best`;
    return "—";
  };

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
          {sessions[0]?.total_volume != null && (
            <button
              className={metric === "volume" ? "active" : ""}
              onClick={() => setMetric("volume")}
            >
              Volume
            </button>
          )}
          {sessions[0]?.best_set_1rm != null && (
            <button
              className={metric === "1rm" ? "active" : ""}
              onClick={() => setMetric("1rm")}
            >
              1RM
            </button>
          )}
          {sessions[0]?.best_set_duration_sec != null && (
            <button
              className={metric === "duration" ? "active" : ""}
              onClick={() => setMetric("duration")}
            >
              Duration
            </button>
          )}
          {sessions[0]?.best_set_pace != null && (
            <button
              className={metric === "pace" ? "active" : ""}
              onClick={() => setMetric("pace")}
            >
              Pace
            </button>
          )}
        </div>
      </div>

      {benchmark && (
        <div className="benchmark-display">
          <span className="benchmark-label">Benchmark:</span>
          <span className="benchmark-value">{formatBenchmark()}</span>
          <span className="benchmark-progress">
            ({benchmark.consecutive_successes}/{3} successes)
          </span>
        </div>
      )}

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
          {[...sessions].reverse().map((s) => (
            <tr key={s.date}>
              <td>{new Date(s.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</td>
              <td>{s.total_sets}</td>
              <td>{getCumulativeStat(s)}</td>
              <td className="set-details-cell">{formatSetDetails(s)}</td>
              <td>{getBestSet(s)}</td>
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
