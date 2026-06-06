# 🔄 System Startup Flow

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    START_ALL Script                          │
│              (One Command to Rule Them All)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │  Step 1: Check Ollama       │
        │  - Is it installed?         │
        │  - Is it running?           │
        │  - Model available?         │
        └─────────────┬───────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
    [Running]              [Not Running]
          │                       │
          │                  Start Ollama
          │                  Pull llama3.2
          │                       │
          └───────────┬───────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │  Step 2: Start Backend      │
        │  - FastAPI Server           │
        │  - Port: 8000               │
        │  - Auto-reload enabled      │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │  Step 3: Start Frontend     │
        │  - React Dev Server         │
        │  - Port: 3001               │
        │  - Hot module reload        │
        └─────────────┬───────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │   ✅ ALL SERVICES READY     │
        │                             │
        │  • Ollama:    :11434        │
        │  • Backend:   :8000         │
        │  • Frontend:  :3001         │
        └─────────────────────────────┘
```

---

## Service Communication Flow

```
┌──────────────┐         HTTP/WS         ┌──────────────┐
│              │ ◄─────────────────────► │              │
│   Browser    │                         │   Backend    │
│  (React UI)  │                         │  (FastAPI)   │
│  Port 3001   │                         │  Port 8000   │
│              │                         │              │
└──────────────┘                         └──────┬───────┘
                                                │
                                          HTTP API
                                                │
                                                ▼
                                       ┌────────────────┐
                                       │                │
                                       │    Ollama      │
                                       │  (LLM Service) │
                                       │   Port 11434   │
                                       │                │
                                       └────────────────┘
```

---

## Data Flow During Evolution

```
User Action (Frontend)
      │
      │  POST /evolve/start
      ▼
Backend Receives Request
      │
      │  Validates input
      │  Creates run record
      ▼
Background Task Started
      │
      │  Initialize population
      ▼
Evolution Loop (per generation)
      │
      ├─► Calculate Fitness
      │       │
      │       ├─► Security Score
      │       ├─► Performance Score
      │       ├─► Scalability Score
      │       └─► Maintainability Score
      │
      ├─► Selection
      │       │
      │       └─► Pick top performers
      │
      ├─► Crossover
      │       │
      │       └─► Combine parent genomes
      │
      ├─► Mutation
      │       │
      │       ├─► Random changes
      │       └─► LLM-guided mutations ⭐
      │
      └─► WebSocket Update
              │
              ▼
        Frontend Receives Update
              │
              ├─► Update charts
              ├─► Show new best
              └─► Display logs
```

---

## Startup Sequence Timeline

```
Time    Event
─────────────────────────────────────────────────────────
0s      User runs START_ALL script
        │
1s      ├─► Check Ollama installation
        │
2s      ├─► Start Ollama (if needed)
        │
3s      ├─► Check for llama3.2 model
        │
5s      ├─► Download model (first time only, ~2-5 min)
        │
6s      ├─► Start Backend (FastAPI)
        │       │
        │       ├─► Load configuration
        │       ├─► Initialize database
        │       ├─► Setup middleware
        │       └─► Register routes
        │
8s      ├─► Backend ready on :8000
        │
9s      ├─► Start Frontend (React)
        │       │
        │       ├─► Install dependencies (first time)
        │       ├─► Compile TypeScript/JSX
        │       └─► Start dev server
        │
12s     ├─► Frontend ready on :3001
        │
13s     └─✅ ALL SERVICES OPERATIONAL
```

---

## Process Tree

```
START_ALL Script (Parent Process)
│
├─► Ollama Service
│   └─► llama3.2 Model (in memory)
│
├─► Backend Terminal Window
│   └─► Python Process
│       ├─► Uvicorn Server
│       ├─► FastAPI Application
│       ├─► Database Connection Pool
│       └─► WebSocket Manager
│
└─► Frontend Terminal Window
    └─► Node.js Process
        ├─► Webpack Dev Server
        ├─► React Application
        └─► Hot Module Reloader
```

---

## Shutdown Sequence

```
User presses Ctrl+C
      │
      ▼
Script receives SIGINT/SIGTERM
      │
      ▼
Cleanup Function Triggered
      │
      ├─► Stop Ollama (if started by script)
      │       │
      │       └─► Graceful shutdown
      │
      ├─► Stop Backend
      │       │
      │       ├─► Close database connections
      │       ├─► Save evolution state
      │       └─► Terminate process
      │
      └─► Stop Frontend
              │
              ├─► Save compilation cache
              └─► Terminate process
      
      ▼
All services stopped
Script exits cleanly
```

---

## Error Handling Flow

```
Service Start Attempt
      │
      ├─► Success
      │       │
      │       └─► Continue to next service
      │
      └─► Failure
              │
              ├─► Critical Service (Backend/Frontend)
              │       │
              │       ├─► Log error
              │       ├─► Show user message
              │       └─► Exit with error code
              │
              └─► Optional Service (Ollama)
                      │
                      ├─► Log warning
                      ├─► Continue anyway
                      └─► Degraded mode
```

---

## Resource Usage

```
Component     CPU      RAM      Disk I/O
─────────────────────────────────────────
Ollama        10-30%   2-4 GB   Low
Backend       5-15%    200 MB   Medium
Frontend      5-10%    300 MB   Low
─────────────────────────────────────────
Total         20-55%   2.5 GB   Medium
```

---

## Port Allocation

```
Port    Service         Protocol   Purpose
──────────────────────────────────────────────────
11434   Ollama          HTTP       LLM inference
8000    Backend         HTTP/WS    API + WebSocket
3001    Frontend        HTTP       React UI
```

---

## First Run vs Subsequent Runs

### First Run
```
┌─────────────────────────────────────┐
│  Total Time: ~5-10 minutes          │
│                                     │
│  - Ollama setup:     1 min          │
│  - Model download:   3-7 min ⏱️     │
│  - Backend start:    30 sec         │
│  - Frontend start:   1-2 min        │
│  - npm install:      (if needed)    │
└─────────────────────────────────────┘
```

### Subsequent Runs
```
┌─────────────────────────────────────┐
│  Total Time: ~15 seconds            │
│                                     │
│  - Ollama check:     2 sec          │
│  - Model check:      1 sec          │
│  - Backend start:    5 sec          │
│  - Frontend start:   7 sec          │
└─────────────────────────────────────┘
```

---

## Production Deployment Alternative

For production, use Docker Compose instead:

```yaml
version: '3.8'
services:
  ollama:
    image: ollama/ollama
    ports: ["11434:11434"]
    
  backend:
    build: ./autonomous-api
    ports: ["8000:8000"]
    depends_on: [ollama]
    
  frontend:
    build: ./reasoning-ui
    ports: ["80:80"]
    depends_on: [backend]
```

```bash
# One command for production
docker-compose up -d
```

---

## Monitoring & Health Checks

```
Health Check Endpoints:

Backend:  GET http://localhost:8000/health
          Returns: {status: "healthy", components: {...}}

Ollama:   GET http://localhost:11434/api/tags
          Returns: List of available models

Frontend: GET http://localhost:3001
          Returns: React application
```

---

This flow ensures reliable, consistent, and user-friendly startup of your entire EvoAPI system! 🚀
