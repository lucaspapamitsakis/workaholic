import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ErrorBoundary from "./components/ErrorBoundary";
import Dashboard from "./pages/Dashboard";
import MuscleGroupPage from "./pages/MuscleGroupPage";
import BenchmarksPage from "./pages/BenchmarksPage";
import SettingsPage from "./pages/SettingsPage";

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="muscle/:muscleTag" element={<MuscleGroupPage />} />
            <Route path="benchmarks" element={<BenchmarksPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
