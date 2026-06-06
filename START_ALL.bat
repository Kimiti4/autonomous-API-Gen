@echo off
REM ========================================================================
REM Autonomous Evolution Engine - Complete Startup Script (Windows)
REM Starts: Ollama (LLM), Backend (FastAPI), Frontend (React)
REM ========================================================================

echo.
echo ========================================
echo   EvoAPI - Complete System Startup
echo ========================================
echo.
echo Starting all services...
echo   1. Ollama (LLM Service)
echo   2. Backend (FastAPI API)
echo   3. Frontend (React UI)
echo.
echo Press Ctrl+C to stop all services
echo ========================================
echo.

REM Check if Ollama is installed
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Ollama not found in PATH
    echo Please install Ollama from: https://ollama.com
    echo Attempting to start anyway...
    echo.
)

REM Start Ollama in background (if not already running)
echo [1/3] Starting Ollama...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo     Ollama is already running
) else (
    echo     Starting Ollama service...
    start "" ollama serve
    timeout /t 3 /nobreak >nul
    echo     Ollama started
)

REM Pull required model if not present
echo     Checking for llama3.2 model...
ollama list | findstr "llama3.2" >nul
if %errorlevel% neq 0 (
    echo     Downloading llama3.2 model (this may take a while)...
    ollama pull llama3.2
) else (
    echo     llama3.2 model already available
)
echo.

REM Start Backend
echo [2/3] Starting Backend (FastAPI)...
cd /d "%~dp0autonomous-api"
start "EvoAPI Backend" cmd /k "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul
echo     Backend starting on http://localhost:8000
echo.

REM Start Frontend
echo [3/3] Starting Frontend (React)...
cd /d "%~dp0reasoning-ui"
start "EvoAPI Frontend" cmd /k "npm start"
timeout /t 2 /nobreak >nul
echo     Frontend starting on http://localhost:3000
echo.

echo ========================================
echo   All Services Started!
echo ========================================
echo.
echo Access Points:
echo   - Frontend UI:  http://localhost:3000
echo   - Backend API:  http://localhost:8000
echo   - API Docs:     http://localhost:8000/docs
echo   - Health Check: http://localhost:8000/health
echo   - WebSocket:    ws://localhost:8000/ws/evolution
echo.
echo To stop all services:
echo   1. Close the terminal windows
echo   2. Or press Ctrl+C in each window
echo.
echo ========================================
echo.

REM Keep this window open
pause
