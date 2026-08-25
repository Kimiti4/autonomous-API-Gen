#!/bin/bash
# Startup script for Autonomous Evolution Engine
# Run this to start both backend and frontend

echo "🧬 Starting Autonomous Evolution Engine v3..."
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the autonomous-api directory"
    exit 1
fi

# Start backend in background
echo "🚀 Starting backend server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend started successfully
if curl -s http://localhost:8000 > /dev/null; then
    echo "✅ Backend is running on http://localhost:8000"
else
    echo "⚠️  Backend may not have started properly"
fi

echo ""
echo "📊 Starting frontend dashboard..."
echo ""

# Navigate to frontend and start
cd reasoning-ui
npm start

# Cleanup on exit
trap "kill $BACKEND_PID 2>/dev/null" EXIT
