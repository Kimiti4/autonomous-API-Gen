#!/bin/bash
# ========================================================================
# Autonomous Evolution Engine - Complete Startup Script (Linux/Mac)
# Starts: Ollama (LLM), Backend (FastAPI), Frontend (React)
# ========================================================================

echo ""
echo "========================================"
echo "  EvoAPI - Complete System Startup"
echo "========================================"
echo ""
echo "Starting all services..."
echo "  1. Ollama (LLM Service)"
echo "  2. Backend (FastAPI API)"
echo "  3. Frontend (React UI)"
echo ""
echo "Press Ctrl+C to stop all services"
echo "========================================"
echo ""

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    
    # Kill background processes
    if [ ! -z "$OLLAMA_PID" ]; then
        echo "  Stopping Ollama..."
        kill $OLLAMA_PID 2>/dev/null
    fi
    
    if [ ! -z "$BACKEND_PID" ]; then
        echo "  Stopping Backend..."
        kill $BACKEND_PID 2>/dev/null
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "  Stopping Frontend..."
        kill $FRONTEND_PID 2>/dev/null
    fi
    
    echo "All services stopped."
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "[WARNING] Ollama not found in PATH"
    echo "Please install Ollama from: https://ollama.com"
    echo "Attempting to start anyway..."
    echo ""
fi

# Start Ollama in background (if not already running)
echo "[1/3] Starting Ollama..."
if pgrep -x "ollama" > /dev/null; then
    echo "    Ollama is already running"
else
    echo "    Starting Ollama service..."
    ollama serve &
    OLLAMA_PID=$!
    sleep 3
    echo "    Ollama started (PID: $OLLAMA_PID)"
fi

# Pull required model if not present
echo "    Checking for llama3.2 model..."
if ollama list | grep -q "llama3.2"; then
    echo "    llama3.2 model already available"
else
    echo "    Downloading llama3.2 model (this may take a while)..."
    ollama pull llama3.2
fi
echo ""

# Start Backend
echo "[2/3] Starting Backend (FastAPI)..."
cd "$SCRIPT_DIR/autonomous-api"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 2
echo "    Backend starting on http://localhost:8000 (PID: $BACKEND_PID)"
echo ""

# Start Frontend
echo "[3/3] Starting Frontend (React)..."
cd "$SCRIPT_DIR/reasoning-ui"
PORT=3001 npm start &
FRONTEND_PID=$!
sleep 2
echo "    Frontend starting on http://localhost:3001 (PID: $FRONTEND_PID)"
echo ""

echo "========================================"
echo "  All Services Started!"
echo "========================================"
echo ""
echo "Access Points:"
echo "  - Frontend UI:  http://localhost:3001"
echo "  - Backend API:  http://localhost:8000"
echo "  - API Docs:     http://localhost:8000/docs"
echo "  - Health Check: http://localhost:8000/health"
echo "  - WebSocket:    ws://localhost:8000/ws/evolution"
echo ""
echo "Process IDs:"
echo "  - Ollama:   $OLLAMA_PID"
echo "  - Backend:  $BACKEND_PID"
echo "  - Frontend: $FRONTEND_PID"
echo ""
echo "To stop all services:"
echo "  Press Ctrl+C in this terminal"
echo "  Or run: kill $OLLAMA_PID $BACKEND_PID $FRONTEND_PID"
echo ""
echo "========================================"
echo ""

# Wait for all background processes
wait
