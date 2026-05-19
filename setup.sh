#!/usr/bin/env bash
# ============================================================
#  QR Transaction System - one-shot setup for macOS / Linux
#
#  Run from the project root:
#      bash setup.sh
#
#  Pre-reqs: Python 3.11+, Node.js 20+, MySQL (XAMPP or local).
#  MySQL must be running before the seed step.
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "=== [1/6] Checking prerequisites ==="
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }
command -v node    >/dev/null 2>&1 || { echo "ERROR: node not found";    exit 1; }
command -v npm     >/dev/null 2>&1 || { echo "ERROR: npm not found";     exit 1; }
python3 --version
node --version

echo
echo "=== [2/6] Copying env templates ==="
if [ -f backend/.env ]; then
    echo "backend/.env already exists - skipped"
else
    cp backend/.env.example backend/.env && echo "Created backend/.env"
fi
if [ -f .env.local ]; then
    echo ".env.local already exists - skipped"
else
    cp .env.local.example .env.local && echo "Created .env.local"
fi

echo
echo "=== [3/6] Creating Python venv ==="
if [ -x backend/venv/bin/python ]; then
    echo "venv already exists - skipped"
else
    python3 -m venv backend/venv
    echo "Created backend/venv"
fi

echo
echo "=== [4/6] Installing Python dependencies ==="
# shellcheck disable=SC1091
source backend/venv/bin/activate
pip install -r backend/requirements.txt

echo
echo "=== [5/6] Installing npm dependencies ==="
npm install

echo
echo "=== [6/6] Setup complete ==="
cat <<'EOF'

Next steps:
  1. Start MySQL (XAMPP Manager -> Start MySQL, or:
       sudo /Applications/XAMPP/xamppfiles/bin/mysql.server start
     )
  2. Create the database (one-time only):
       /Applications/XAMPP/xamppfiles/bin/mysql -u root -e \
         "CREATE DATABASE IF NOT EXISTS qr_transaction;"
  3. Seed sample data (one-time only):
       cd backend
       source venv/bin/activate
       python seed_database.py
  4. Start the backend (keep this terminal open):
       cd backend
       source venv/bin/activate
       python run.py
  5. In a new terminal, start the frontend:
       npm run dev

Open http://localhost:3000 in your browser.
Login credentials are shown on the /login page.
EOF
