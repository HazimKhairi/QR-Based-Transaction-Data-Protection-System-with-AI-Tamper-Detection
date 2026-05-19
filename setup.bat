@echo off
REM ============================================================
REM  QR Transaction System - one-shot setup for Windows
REM
REM  Run by double-clicking or:
REM      setup.bat
REM
REM  Pre-reqs: Python 3.11+, Node.js 20+, XAMPP installed.
REM  MySQL must be started from the XAMPP Control Panel before
REM  the seed step runs.
REM ============================================================

setlocal enableextensions
cd /d "%~dp0"

echo.
echo === [1/6] Checking prerequisites ===
where python >nul 2>nul || (echo ERROR: python not found in PATH. Install Python 3.11+ from https://python.org && exit /b 1)
where node   >nul 2>nul || (echo ERROR: node not found in PATH. Install Node.js 20+ from https://nodejs.org && exit /b 1)
where npm    >nul 2>nul || (echo ERROR: npm not found in PATH. && exit /b 1)
python --version
node --version

echo.
echo === [2/6] Copying env templates ===
if exist backend\.env (
    echo backend\.env already exists - skipped
) else (
    copy /Y backend\.env.example backend\.env >nul && echo Created backend\.env
)
if exist .env.local (
    echo .env.local already exists - skipped
) else (
    copy /Y .env.local.example .env.local >nul && echo Created .env.local
)

echo.
echo === [3/6] Creating Python venv ===
if exist backend\venv\Scripts\python.exe (
    echo venv already exists - skipped
) else (
    python -m venv backend\venv || (echo ERROR: failed to create venv && exit /b 1)
    echo Created backend\venv
)

echo.
echo === [4/6] Installing Python dependencies ===
call backend\venv\Scripts\activate.bat
pip install -r backend\requirements.txt || (echo ERROR: pip install failed && exit /b 1)

echo.
echo === [5/6] Installing npm dependencies ===
call npm install || (echo ERROR: npm install failed && exit /b 1)

echo.
echo === [6/6] Setup complete ===
echo.
echo Next steps:
echo   1. Open XAMPP Control Panel and click Start next to MySQL.
echo   2. Create the database (one-time only):
echo        "C:\xampp\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE IF NOT EXISTS qr_transaction;"
echo   3. Seed sample data (one-time only):
echo        cd backend
echo        venv\Scripts\activate
echo        python seed_database.py
echo   4. Start the backend (keep this terminal open):
echo        cd backend
echo        venv\Scripts\activate
echo        python run.py
echo   5. In a new terminal, start the frontend:
echo        npm run dev
echo.
echo Then open http://localhost:3000 in your browser.
echo Login credentials are shown on the /login page itself.
echo.
pause
endlocal
