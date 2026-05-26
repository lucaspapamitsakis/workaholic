import { Outlet, NavLink, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import "./Layout.css";

export default function Layout() {
  const [muscleGroups, setMuscleGroups] = useState<string[]>([]);
  const location = useLocation();

  useEffect(() => {
    api.getMuscleGroups().then(setMuscleGroups).catch(() => {});
  }, [location.pathname]);

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>Workout Tracker</h1>
        </div>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
          <NavLink to="/benchmarks" className={({ isActive }) => (isActive ? "active" : "")}>
            Benchmarks
          </NavLink>
          <div className="nav-section">
            <span className="nav-section-title">Muscle Groups</span>
            {muscleGroups.map((tag) => (
              <NavLink
                key={tag}
                to={`/muscle/${encodeURIComponent(tag)}`}
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                {tag}
              </NavLink>
            ))}
          </div>
          <NavLink to="/settings" className={({ isActive }) => (isActive ? "active" : "")}>
            Settings
          </NavLink>
        </nav>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
