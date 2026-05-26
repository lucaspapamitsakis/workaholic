import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import ExerciseCard from "../components/ExerciseCard";
import "./MuscleGroupPage.css";

export default function MuscleGroupPage() {
  const { muscleTag } = useParams<{ muscleTag: string }>();
  const [exercises, setExercises] = useState<string[]>([]);

  useEffect(() => {
    if (muscleTag) {
      api
        .getExercisesForMuscle(decodeURIComponent(muscleTag))
        .then(setExercises)
        .catch(() => setExercises([]));
    }
  }, [muscleTag]);

  if (!muscleTag) return null;

  return (
    <div className="muscle-group-page">
      <h2>{decodeURIComponent(muscleTag)}</h2>
      <div className="exercises-list">
        {exercises.length === 0 ? (
          <p className="empty-state">No exercises found for this muscle group.</p>
        ) : (
          exercises.map((name) => <ExerciseCard key={name} exerciseName={name} />)
        )}
      </div>
    </div>
  );
}
