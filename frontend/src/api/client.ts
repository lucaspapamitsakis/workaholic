const BASE_URL = "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export interface ExerciseSet {
  id: number;
  date: string;
  session_duration_min: number | null;
  workout_type: string | null;
  exercise_name: string;
  primary_muscle_tag: string;
  secondary_muscle_tags: string[] | null;
  set_number: number;
  weight_lbs: number | null;
  reps: number | null;
  duration_sec: number | null;
  distance_m: number | null;
  is_benchmark_set: boolean;
  volume: number | null;
  estimated_1rm: number | null;
  pace_sec_per_m: number | null;
}

export interface ExerciseSessionAggregate {
  date: string;
  exercise_name: string;
  total_sets: number;
  total_volume: number | null;
  total_reps: number | null;
  best_set_weight: number | null;
  best_set_reps: number | null;
  best_set_1rm: number | null;
  best_set_duration_sec: number | null;
  best_set_pace: number | null;
  best_reps_in_session: number | null;
  benchmark_reached: boolean;
  set_details: ExerciseSet[];
}

export interface Benchmark {
  id: number;
  exercise_name: string;
  benchmark_type: string;
  benchmark_weight: number | null;
  benchmark_reps: number | null;
  benchmark_duration_sec: number | null;
  benchmark_pace_sec_per_m: number | null;
  increment_weight_lbs: number;
  increment_reps: number;
  increment_duration_sec: number;
  increment_pace_sec_per_m: number | null;
  consecutive_successes: number;
  last_evaluated_date: string | null;
}

export interface SessionSummary {
  date: string;
  session_duration_min: number | null;
  workout_type: string | null;
  exercises: string[];
  total_volume: number | null;
}

export interface SyncResult {
  files_scanned: number;
  files_parsed: number;
  sets_added: number;
  errors: string[];
  notifications: { exercise_name: string; message: string; notification_type: string }[];
  scanned_paths: string[];
  skipped_paths: string[];
}

export interface AppConfig {
  obsidian_vault_path: string;
  notes_subfolder: string;
  visualization_session_count: number;
  default_weight_increment_lbs: number;
  default_reps_increment: number;
  default_duration_increment_sec: number;
  default_pace_increment_sec_per_m: number;
  consolidation_threshold: number;
}

export interface WorkoutTypeCount {
  workout_type: string;
  count: number;
}

export interface WorkoutSummary {
  period_days: number;
  start_date: string;
  end_date: string;
  total_sessions: number;
  by_type: WorkoutTypeCount[];
}

export interface BenchmarkHistory {
  id: number;
  exercise_name: string;
  old_weight: number | null;
  old_reps: number | null;
  old_duration_sec: number | null;
  old_pace: number | null;
  new_weight: number | null;
  new_reps: number | null;
  new_duration_sec: number | null;
  new_pace: number | null;
  reason: string | null;
  consolidated_at: string;
}

export interface BenchmarkIncrementUpdate {
  increment_weight_lbs?: number;
  increment_reps?: number;
  increment_duration_sec?: number;
  increment_pace_sec_per_m?: number;
}

export const api = {
  getMuscleGroups: () => request<string[]>("/exercises/muscle-groups"),

  getExercisesForMuscle: (tag: string) =>
    request<string[]>(`/exercises/by-muscle/${encodeURIComponent(tag)}`),

  getExerciseSessions: (name: string, limit?: number) =>
    request<ExerciseSessionAggregate[]>(
      `/exercises/${encodeURIComponent(name)}/sessions${limit ? `?limit=${limit}` : ""}`
    ),

  getExerciseBenchmark: (name: string) =>
    request<Benchmark | null>(`/exercises/${encodeURIComponent(name)}/benchmark`),

  getAllBenchmarks: () => request<Benchmark[]>("/benchmarks"),

  updateBenchmarkIncrements: (name: string, data: BenchmarkIncrementUpdate) =>
    request<Benchmark>(`/benchmarks/${encodeURIComponent(name)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  getBenchmarkHistory: (name: string) =>
    request<BenchmarkHistory[]>(`/benchmarks/${encodeURIComponent(name)}/history`),

  getRecentSessions: (limit = 10) =>
    request<SessionSummary[]>(`/sessions?limit=${limit}`),

  getWorkoutSummary: (days = 30) =>
    request<WorkoutSummary>(`/sessions/summary?days=${days}`),

  triggerSync: () => request<SyncResult>("/sync", { method: "POST" }),

  getConfig: () => request<AppConfig>("/config"),

  updateConfig: (data: Partial<AppConfig>) =>
    request<AppConfig>("/config", { method: "PATCH", body: JSON.stringify(data) }),
};
