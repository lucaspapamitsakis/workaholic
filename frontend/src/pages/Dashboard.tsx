import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SessionSummary, SyncResult } from "../api/client";
import "./Dashboard.css";

export default function Dashboard() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);

  useEffect(() => {
    api.getRecentSessions(10).then(setSessions).catch(() => {});
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setSyncError(null);
    try {
      const result = await api.triggerSync();
      setSyncResult(result);
      const updated = await api.getRecentSessions(10);
      setSessions(updated);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      console.error("Sync failed:", e);
      setSyncError(
        `Sync request failed: ${msg}. The backend may not be running. ` +
          `Check the terminal where you ran ./run.sh for errors.`
      );
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Dashboard</h2>
        <button className="primary" onClick={handleSync} disabled={syncing}>
          {syncing ? "Syncing..." : "Sync Notes"}
        </button>
      </div>

      {syncError && (
        <div className="card sync-result">
          <div className="notification error">{syncError}</div>
        </div>
      )}

      {syncResult && (
        <div className="card sync-result">
          <p>
            Scanned {syncResult.files_scanned ?? 0} files, parsed{" "}
            {syncResult.files_parsed ?? 0}, added {syncResult.sets_added ?? 0} sets.
          </p>
          {(syncResult.notifications ?? []).map((n, i) => (
            <div key={i} className="notification">
              <span className="badge success">{n.notification_type}</span>{" "}
              {n.message}
            </div>
          ))}
          {(syncResult.errors ?? []).map((e, i) => (
            <div key={i} className="notification error">
              {e}
            </div>
          ))}
          {(syncResult.scanned_paths ?? []).length > 0 && (
            <details className="sync-paths">
              <summary>
                {syncResult.scanned_paths.length} files scanned
                {(syncResult.skipped_paths ?? []).length > 0 &&
                  ` (${syncResult.skipped_paths.length} unchanged, skipped)`}
              </summary>
              <ul>
                {syncResult.scanned_paths.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      <h3>Recent Sessions</h3>
      {sessions.length === 0 ? (
        <p className="empty-state">
          No sessions yet. Configure your Obsidian vault path in Settings, then
          sync your notes.
        </p>
      ) : (
        <div className="sessions-grid">
          {sessions.map((s) => (
            <div key={s.date} className="card session-card">
              <div className="session-date">{s.date}</div>
              <div className="session-type">
                <span className="badge warning">{s.workout_type || "—"}</span>
                {s.session_duration_min && (
                  <span className="session-duration">
                    {s.session_duration_min} min
                  </span>
                )}
              </div>
              <ul className="session-exercises">
                {s.exercises.map((ex) => (
                  <li key={ex}>{ex}</li>
                ))}
              </ul>
              {s.total_volume != null && (
                <div className="session-volume">
                  Volume: {s.total_volume.toLocaleString()} lbs
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
