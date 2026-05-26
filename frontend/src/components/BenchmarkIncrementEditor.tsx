import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Benchmark, BenchmarkIncrementUpdate } from "../api/client";
import "./BenchmarkIncrementEditor.css";

interface Props {
  benchmark: Benchmark;
  onSaved: (updated: Benchmark) => void;
}

/**
 * Inline editor for a benchmark's increment configuration.
 *
 * Renders a small pencil-icon button. Clicking it pops up a panel exposing
 * only the increment field(s) that are relevant to the benchmark's type:
 *   - weight_reps: weight + reps increment
 *   - reps:        reps increment only
 *   - duration:    duration increment only
 *   - pace:        pace increment only
 *
 * Closes on outside click, Escape, or after a successful save.
 */
export default function BenchmarkIncrementEditor({ benchmark, onSaved }: Props) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<BenchmarkIncrementUpdate>({});
  const popoverRef = useRef<HTMLDivElement>(null);

  // Reset draft when opening so we always start from current values.
  useEffect(() => {
    if (open) {
      setDraft({
        increment_weight_lbs: benchmark.increment_weight_lbs ?? undefined,
        increment_reps: benchmark.increment_reps ?? undefined,
        increment_duration_sec: benchmark.increment_duration_sec ?? undefined,
        increment_pace_sec_per_m: benchmark.increment_pace_sec_per_m ?? undefined,
      });
      setError(null);
    }
  }, [open, benchmark]);

  // Close on Escape or outside click.
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const handleClick = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handleKey);
    document.addEventListener("mousedown", handleClick);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.removeEventListener("mousedown", handleClick);
    };
  }, [open]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      // Send only the fields relevant to this benchmark type to avoid
      // overwriting unrelated values.
      const payload: BenchmarkIncrementUpdate = {};
      if (benchmark.benchmark_type === "weight_reps") {
        payload.increment_weight_lbs = draft.increment_weight_lbs;
        payload.increment_reps = draft.increment_reps;
      } else if (benchmark.benchmark_type === "reps") {
        payload.increment_reps = draft.increment_reps;
      } else if (benchmark.benchmark_type === "duration") {
        payload.increment_duration_sec = draft.increment_duration_sec;
      } else if (benchmark.benchmark_type === "pace") {
        payload.increment_pace_sec_per_m = draft.increment_pace_sec_per_m;
      }
      const updated = await api.updateBenchmarkIncrements(
        benchmark.exercise_name,
        payload
      );
      onSaved(updated);
      setOpen(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="benchmark-increment-editor" ref={popoverRef}>
      <button
        className="increment-toggle"
        title="Edit benchmark increment"
        onClick={() => setOpen((o) => !o)}
        type="button"
      >
        ✎
      </button>

      {open && (
        <div className="increment-popover">
          <div className="increment-popover-title">
            Increment per consolidation
          </div>

          {benchmark.benchmark_type === "weight_reps" && (
            <>
              <div className="increment-field">
                <label>Weight (lbs)</label>
                <input
                  type="number"
                  step={2.5}
                  min={0}
                  value={draft.increment_weight_lbs ?? ""}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      increment_weight_lbs:
                        e.target.value === "" ? undefined : parseFloat(e.target.value),
                    })
                  }
                />
              </div>
              <div className="increment-field">
                <label>Reps</label>
                <input
                  type="number"
                  step={1}
                  min={0}
                  value={draft.increment_reps ?? ""}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      increment_reps:
                        e.target.value === "" ? undefined : parseInt(e.target.value),
                    })
                  }
                />
              </div>
            </>
          )}

          {benchmark.benchmark_type === "reps" && (
            <div className="increment-field">
              <label>Reps</label>
              <input
                type="number"
                step={1}
                min={1}
                value={draft.increment_reps ?? ""}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    increment_reps:
                      e.target.value === "" ? undefined : parseInt(e.target.value),
                  })
                }
              />
            </div>
          )}

          {benchmark.benchmark_type === "duration" && (
            <div className="increment-field">
              <label>Duration (sec)</label>
              <input
                type="number"
                step={1}
                min={1}
                value={draft.increment_duration_sec ?? ""}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    increment_duration_sec:
                      e.target.value === "" ? undefined : parseFloat(e.target.value),
                  })
                }
              />
            </div>
          )}

          {benchmark.benchmark_type === "pace" && (
            <div className="increment-field">
              <label>Pace (sec/m faster)</label>
              <input
                type="number"
                step={0.001}
                min={0}
                value={draft.increment_pace_sec_per_m ?? ""}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    increment_pace_sec_per_m:
                      e.target.value === "" ? undefined : parseFloat(e.target.value),
                  })
                }
              />
              <span className="increment-hint">
                {draft.increment_pace_sec_per_m
                  ? `≈ ${(draft.increment_pace_sec_per_m * 500).toFixed(2)} sec/500m faster`
                  : ""}
              </span>
            </div>
          )}

          {error && <div className="increment-error">{error}</div>}

          <div className="increment-actions">
            <button className="ghost" onClick={() => setOpen(false)} disabled={saving}>
              Cancel
            </button>
            <button className="primary" onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
