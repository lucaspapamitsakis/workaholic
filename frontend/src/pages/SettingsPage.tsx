import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AppConfig } from "../api/client";
import "./SettingsPage.css";

export default function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getConfig().then(setConfig).catch(() => {});
  }, []);

  const handleSave = async () => {
    if (!config) return;
    try {
      const updated = await api.updateConfig(config);
      setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  if (!config) return <p>Loading...</p>;

  return (
    <div className="settings-page">
      <h2>Settings</h2>

      <div className="card settings-form">
        <div className="form-group">
          <label>Obsidian Vault Path</label>
          <input
            type="text"
            value={config.obsidian_vault_path}
            onChange={(e) => setConfig({ ...config, obsidian_vault_path: e.target.value })}
            placeholder="/path/to/your/obsidian/vault"
          />
          <span className="form-help">Absolute path to your Obsidian vault root</span>
        </div>

        <div className="form-group">
          <label>Notes Subfolder</label>
          <input
            type="text"
            value={config.notes_subfolder}
            onChange={(e) => setConfig({ ...config, notes_subfolder: e.target.value })}
            placeholder="e.g. Exercise Logs"
          />
          <span className="form-help">Subfolder within the vault where exercise notes live</span>
        </div>

        <div className="form-group">
          <label>Sessions to Visualize</label>
          <input
            type="number"
            value={config.visualization_session_count}
            onChange={(e) =>
              setConfig({ ...config, visualization_session_count: parseInt(e.target.value) || 4 })
            }
            min={1}
            max={20}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Weight Increment (lbs)</label>
            <input
              type="number"
              value={config.default_weight_increment_lbs}
              onChange={(e) =>
                setConfig({ ...config, default_weight_increment_lbs: parseFloat(e.target.value) || 5 })
              }
              step={2.5}
              min={0}
            />
          </div>
          <div className="form-group">
            <label>Reps Increment</label>
            <input
              type="number"
              value={config.default_reps_increment}
              onChange={(e) =>
                setConfig({ ...config, default_reps_increment: parseInt(e.target.value) || 2 })
              }
              min={1}
            />
          </div>
          <div className="form-group">
            <label>Duration Increment (sec)</label>
            <input
              type="number"
              value={config.default_duration_increment_sec}
              onChange={(e) =>
                setConfig({ ...config, default_duration_increment_sec: parseFloat(e.target.value) || 5 })
              }
              min={1}
            />
          </div>
        </div>

        <div className="form-group">
          <label>Consolidation Threshold</label>
          <input
            type="number"
            value={config.consolidation_threshold}
            onChange={(e) =>
              setConfig({ ...config, consolidation_threshold: parseInt(e.target.value) || 3 })
            }
            min={1}
            max={10}
          />
          <span className="form-help">
            Number of consecutive successful sessions before benchmark auto-increments
          </span>
        </div>

        <button className="primary" onClick={handleSave}>
          {saved ? "Saved!" : "Save Settings"}
        </button>
      </div>
    </div>
  );
}
