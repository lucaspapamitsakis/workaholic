import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SessionSummary, SyncResult } from "../api/client";
import "./Dashboard.css";

export default function Dashboard() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    api.getRecentSessions(10).then(setSessions).catch(() => {});
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await api.triggerSync();
      setSyncResult(result);
      const updated = await api.getRecentSessions(10);
      setSessions(updated);
    } catch (e) {
      console.error(e);
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

      {syncResult && (
        <div className="card sync-result">
          <p>
            Scanned {syncResult.files_scanned} files, parsed{" "}
            {syncResult.files_parsed}, added {syncResult.sets_added} sets.
          </p>
          {syncResult.notifications.map((n, i) => (
            <div key={i} className="notification">
              <span className="badge success">{n.notification_type}</span>{" "}
              {n.message}
            </div>
          ))}
          {syncResult.errors.map((e, i) => (
            <div key={i} className="notification error">
              {e}
            </div>
          ))}
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
