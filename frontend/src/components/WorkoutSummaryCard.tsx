import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { WorkoutSummary } from "../api/client";
import { formatShortDate } from "../utils/format";
import "./WorkoutSummaryCard.css";

const PERIOD_OPTIONS: number[] = [7, 30, 90];

/**
 * "Training balance" widget for the Dashboard.
 *
 * Shows how many of each workout type (Push/Pull/Legs/Cardio/…) you've logged
 * in the selected period. The bars are sized proportionally to the most
 * common type so any imbalance is visually obvious.
 */
export default function WorkoutSummaryCard() {
  const [summary, setSummary] = useState<WorkoutSummary | null>(null);
  const [days, setDays] = useState<number>(30);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    setLoading(true);
    api
      .getWorkoutSummary(days)
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
  }, [days]);

  const maxCount = summary?.by_type.reduce((m, t) => Math.max(m, t.count), 0) ?? 0;

  return (
    <div className="card workout-summary-card">
      <div className="workout-summary-header">
        <h3>Training balance</h3>
        <div className="period-selector">
          {PERIOD_OPTIONS.map((d) => (
            <button
              key={d}
              className={days === d ? "active" : ""}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : !summary || summary.total_sessions === 0 ? (
        <p className="muted">
          No sessions logged in the last {days} day{days === 1 ? "" : "s"}.
        </p>
      ) : (
        <>
          <div className="workout-summary-period">
            {formatShortDate(summary.start_date)} – {formatShortDate(summary.end_date)} ·{" "}
            <strong>{summary.total_sessions}</strong> session
            {summary.total_sessions === 1 ? "" : "s"}
          </div>
          <ul className="workout-summary-bars">
            {summary.by_type.map((t) => (
              <li key={t.workout_type}>
                <span className="bar-label">{t.workout_type}</span>
                <span className="bar-track">
                  <span
                    className="bar-fill"
                    style={{
                      width: `${maxCount > 0 ? (t.count / maxCount) * 100 : 0}%`,
                    }}
                  />
                </span>
                <span className="bar-count">{t.count}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
