# ========================================================================
# Autonomous Evolution Engine - Complete Startup Script (PowerShell)
# Starts: Ollama (LLM), Backend (FastAPI), Frontend (React)
# ========================================================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  EvoAPI - Complete System Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting all services..." -ForegroundColor Yellow
Write-Host "  1. Ollama (LLM Service)"
Write-Host "  2. Backend (FastAPI API)"
Write-Host "  3. Frontend (React UI)"
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Function to cleanup on exit
function Cleanup {
    Write-Host ""
    Write-Host "Shutting down services..." -ForegroundColor Yellow
    
    if ($OllamaProcess) {
        Write-Host "  Stopping Ollama..."
        Stop-Process -Id $OllamaProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    if ($BackendProcess) {
        Write-Host "  Stopping Backend..."
        Stop-Process -Id $BackendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    if ($FrontendProcess) {
        Write-Host "  Stopping Frontend..."
        Stop-Process -Id $FrontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "All services stopped." -ForegroundColor Green
    exit 0
}

# Register cleanup on Ctrl+C
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup } | Out-Null

# Check if Ollama is installed
Write-Host "[1/3] Starting Ollama..." -ForegroundColor Green
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    # Check if Ollama is already running
    $OllamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
    if ($OllamaRunning) {
        Write-Host "    Ollama is already running" -ForegroundColor Gray
    } else {
        Write-Host "    Starting Ollama service..." -ForegroundColor Gray
        $OllamaProcess = Start-Process ollama -ArgumentList "serve" -PassThru -WindowStyle Hidden
        Start-Sleep -Seconds 3
        Write-Host "    Ollama started (PID: $($OllamaProcess.Id))" -ForegroundColor Gray
    }
    
    # Pull required model if not present
    Write-Host "    Checking for llama3.2 model..." -ForegroundColor Gray
    $ModelList = & ollama list 2>&1
    if ($ModelList -match "llama3.2") {
        Write-Host "    llama3.2 model already available" -ForegroundColor Gray
    } else {
        Write-Host "    Downloading llama3.2 model (this may take a while)..." -ForegroundColor Yellow
        & ollama pull llama3.2
    }
} else {
    Write-Host "    [WARNING] Ollama not found in PATH" -ForegroundColor Red
    Write-Host "    Please install Ollama from: https://ollama.com" -ForegroundColor Red
    Write-Host "    Attempting to start anyway..." -ForegroundColor Yellow
}
Write-Host ""

# Start Backend
Write-Host "[2/3] Starting Backend (FastAPI)..." -ForegroundColor Green
Set-Location "$ScriptDir\autonomous-api"
$BackendProcess = Start-Process python -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" -PassThru -WindowStyle Normal
Start-Sleep -Seconds 2
Write-Host "    Backend starting on http://localhost:8000 (PID: $($BackendProcess.Id))" -ForegroundColor Gray
Write-Host ""

# Start Frontend
Write-Host "[3/3] Starting Frontend (React)..." -ForegroundColor Green
Set-Location "$ScriptDir\reasoning-ui"
$env:PORT = "3001"
$FrontendProcess = Start-Process npm -ArgumentList "start" -PassThru -WindowStyle Normal
Start-Sleep -Seconds 2
Write-Host "    Frontend starting on http://localhost:3001 (PID: $($FrontendProcess.Id))" -ForegroundColor Gray
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access Points:" -ForegroundColor Yellow
Write-Host "  - Frontend UI:  http://localhost:3001" -ForegroundColor White
Write-Host "  - Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "  - API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Health Check: http://localhost:8000/health" -ForegroundColor White
Write-Host "  - WebSocket:    ws://localhost:8000/ws/evolution" -ForegroundColor White
Write-Host ""
Write-Host "Process IDs:" -ForegroundColor Yellow
if ($OllamaProcess) { Write-Host "  - Ollama:   $($OllamaProcess.Id)" -ForegroundColor White }
if ($BackendProcess) { Write-Host "  - Backend:  $($BackendProcess.Id)" -ForegroundColor White }
if ($FrontendProcess) { Write-Host "  - Frontend: $($FrontendProcess.Id)" -ForegroundColor White }
Write-Host ""
Write-Host "To stop all services:" -ForegroundColor Yellow
Write-Host "  Press Ctrl+C in this terminal" -ForegroundColor White
Write-Host "  Or close the terminal windows" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
        
        # Check if processes are still running
        if ($BackendProcess -and $BackendProcess.HasExited) {
            Write-Host "Backend process exited" -ForegroundColor Red
            break
        }
        
        if ($FrontendProcess -and $FrontendProcess.HasExited) {
            Write-Host "Frontend process exited" -ForegroundColor Red
            break
        }
    }
} finally {
    Cleanup
}
