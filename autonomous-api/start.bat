@echo off
REM Startup script for Autonomous Evolution Engine (Windows)
REM Run this to start both backend and frontend

echo.
echo ========================================
echo   Autonomous Evolution Engine v3
echo ========================================
echo.

REM Check if we're in the right directory
if not exist "pyproject.toml" (
    echo ERROR: Please run this script from the autonomous-api directory
    pause
    exit /b 1
)

REM Start backend in background
echo Starting backend server...
start "Backend Server" cmd /k "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo.
echo Backend should be running on http://localhost:8000
echo.
echo Starting frontend dashboard...
echo.

REM Navigate to frontend and start
cd reasoning-ui
start "Frontend Dashboard" cmd /k "npm start"

echo.
echo ========================================
echo   Both servers are starting!
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:3000
echo ========================================
echo.
pause
