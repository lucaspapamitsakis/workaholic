#!/bin/bash
# Start the Workout Progression Tracker.
#
# Robust behavior:
#   * Kills any stale processes on ports 8000 / 5173 before starting,
#     so you never end up with the previous backend serving old code.
#   * Verifies the backend actually started (port 8000 listening) before
#     declaring success.
#
# Usage: ./run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_PORT=8000
FRONTEND_PORT=5173

free_port() {
    local port=$1
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo "  Stopping stale process(es) on port $port: $pids"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 0.5
    fi
}

echo "Preparing ports..."
free_port "$BACKEND_PORT"
free_port "$FRONTEND_PORT"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Starting Workout Progression Tracker..."
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
echo ""

cd backend
uvicorn app.main:app --reload --port "$BACKEND_PORT" &
BACKEND_PID=$!
cd ..

cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

cleanup() {
    echo ""
    echo "Stopping servers..."
    kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
    free_port "$BACKEND_PORT"
    free_port "$FRONTEND_PORT"
}
trap cleanup EXIT INT TERM

# Wait briefly and verify the backend really came up.
sleep 2
if ! lsof -i :"$BACKEND_PORT" >/dev/null 2>&1; then
    echo ""
    echo "ERROR: Backend failed to start on port $BACKEND_PORT."
    echo "Check the output above for the actual cause (port still in use,"
    echo "import errors, missing dependencies, etc.)."
    exit 1
fi

echo "Both servers are up. Press Ctrl+C to stop."
wait
