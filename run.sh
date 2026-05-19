#!/usr/bin/env bash
# ============================================================
#  QR Transaction System - launch backend + frontend (Unix)
#
#  Pre-req: bash setup.sh once, and MySQL running.
#
#  Both processes run in this shell. Press Ctrl+C to stop both.
# ============================================================
set -uo pipefail
cd "$(dirname "$0")"

free_port() {
    local port="$1"
    local pid
    pid=$(lsof -t -i :"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Killing PID $pid on port $port"
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

echo
echo "=== Freeing ports 5000 and 3000 if busy ==="
free_port 5000
free_port 3000

echo
echo "=== Sanity check ==="
[ -x backend/venv/bin/python ] || { echo "ERROR: backend/venv missing. Run bash setup.sh first."; exit 1; }
[ -d node_modules ]            || { echo "ERROR: node_modules missing. Run bash setup.sh first."; exit 1; }
[ -f backend/.env ]            || { echo "ERROR: backend/.env missing. Run bash setup.sh first."; exit 1; }

BACK_PID=""
FRONT_PID=""

cleanup() {
    echo
    echo "Stopping servers..."
    [ -n "$BACK_PID" ]  && kill "$BACK_PID"  2>/dev/null || true
    [ -n "$FRONT_PID" ] && kill "$FRONT_PID" 2>/dev/null || true
    wait 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

echo
echo "=== Starting backend (logs: /tmp/qr-backend.log) ==="
( cd backend && source venv/bin/activate && python run.py ) >/tmp/qr-backend.log 2>&1 &
BACK_PID=$!
echo "Backend PID $BACK_PID — http://localhost:5000"

sleep 3

echo
echo "=== Starting frontend (logs: /tmp/qr-frontend.log) ==="
npm run dev >/tmp/qr-frontend.log 2>&1 &
FRONT_PID=$!
echo "Frontend PID $FRONT_PID — http://localhost:3000"

echo
echo "============================================================"
echo "  Backend:  http://localhost:5000   (tail -f /tmp/qr-backend.log)"
echo "  Frontend: http://localhost:3000   (tail -f /tmp/qr-frontend.log)"
echo
echo "  Press Ctrl+C to stop both."
echo "============================================================"

wait
