@echo off
REM ============================================================
REM  QR Transaction System - launch backend + frontend (Windows)
REM
REM  Pre-req: run setup.bat once and start MySQL in XAMPP.
REM
REM  Double-click this file. Two console windows will open:
REM    - QR Backend  (port 5000)
REM    - QR Frontend (port 3000)
REM  Close either window to stop that server.
REM ============================================================

setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0"

echo.
echo === Freeing ports 5000 and 3000 if busy ===
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING 2^>nul') do (
    echo Killing PID %%P on port 5000
    taskkill /F /PID %%P >nul 2>nul
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING 2^>nul') do (
    echo Killing PID %%P on port 3000
    taskkill /F /PID %%P >nul 2>nul
)

REM Kill any leftover Next.js dev workers for this project + clear the
REM dev lock file so 'next dev' can acquire it cleanly.
taskkill /F /FI "WINDOWTITLE eq QR Frontend*" >nul 2>nul
if exist .next\dev\lock (
    echo Removing stale .next\dev\lock
    del /F /Q .next\dev\lock >nul 2>nul
)

echo.
echo === Sanity check ===
if not exist backend\venv\Scripts\python.exe (
    echo ERROR: backend\venv missing. Run setup.bat first.
    pause
    exit /b 1
)
if not exist node_modules (
    echo ERROR: node_modules missing. Run setup.bat first.
    pause
    exit /b 1
)
if not exist backend\.env (
    echo ERROR: backend\.env missing. Run setup.bat first.
    pause
    exit /b 1
)

echo.
echo === Launching backend in a new window ===
start "QR Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate.bat && python run.py"

echo Waiting 3 seconds for backend to come up...
timeout /t 3 /nobreak >nul

echo.
echo === Launching frontend in a new window ===
start "QR Frontend" cmd /k "cd /d %~dp0 && npm run dev"

echo.
echo ============================================================
echo  Backend:  http://localhost:5000
echo  Frontend: http://localhost:3000
echo.
echo  Close the QR Backend / QR Frontend windows to stop them.
echo ============================================================
echo.
pause
endlocal
