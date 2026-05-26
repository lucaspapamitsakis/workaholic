#!/bin/bash
# Start the Workout Progression Tracker
# Usage: ./run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Starting Workout Progression Tracker..."
echo "  Backend: http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""

# Start backend
cd backend
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend dev server
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Trap to kill both on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

echo "Press Ctrl+C to stop."
wait
