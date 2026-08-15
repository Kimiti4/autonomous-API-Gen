# 🧬 Autonomous Evolution Engine — User Guide

**Version 3.1.0 — Production-Grade Genetic API Architecture Generator**

A complete end-user manual for installing, configuring, and operating the Autonomous Evolution Engine — a system that uses genetic algorithms to evolve, evaluate, and generate production-ready FastAPI microservice architectures.

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Requirements](#2-system-requirements)
3. [Quick Start (5 Minutes)](#3-quick-start-5-minutes)
4. [Installation](#4-installation)
   - [Backend Setup](#41-backend-setup)
   - [Frontend Setup](#42-frontend-setup)
   - [Docker Setup (Optional)](#43-docker-setup-optional)
5. [Configuration](#5-configuration)
   - [Environment Variables](#51-environment-variables)
   - [CORS Configuration](#52-cors-configuration)
   - [Rate Limiting](#53-rate-limiting)
6. [Running the System](#6-running-the-system)
   - [Starting the Backend](#61-starting-the-backend)
   - [Starting the Frontend](#62-starting-the-frontend)
   - [Quick Startup Scripts](#63-quick-startup-scripts)
7. [Using the Web Dashboard](#7-using-the-web-dashboard)
   - [Dashboard Overview](#71-dashboard-overview)
   - [Standard Evolution](#72-standard-evolution)
   - [Elite Evolution](#73-elite-evolution)
   - [Synchronous Quick Test](#74-synchronous-quick-test)
   - [Viewing Results](#75-viewing-results)
8. [Using the REST API](#8-using-the-rest-api)
   - [Health Check](#81-health-check)
   - [Standard Evolution (Async)](#82-standard-evolution-async)
   - [Standard Evolution (Sync)](#83-standard-evolution-sync)
   - [Elite Evolution](#84-elite-evolution)
   - [Production Readiness Gate](#85-production-readiness-gate)
   - [Elite Insights & Memory](#86-elite-insights--memory)
9. [WebSocket Real-Time Updates](#9-websocket-real-time-updates)
10. [Understanding Genomes](#10-understanding-genomes)
    - [Genome Structure](#101-genome-structure)
    - [Genes and Their Meanings](#102-genes-and-their-meanings)
11. [Understanding Fitness Scoring](#11-understanding-fitness-scoring)
    - [Fitness Components](#111-fitness-components)
    - [Production Fitness Scoring](#112-production-fitness-scoring)
    - [Security Scoring](#113-security-scoring)
12. [Elite Mode Features](#12-elite-mode-features)
    - [Multi-Population System](#121-multi-population-system)
    - [Adaptive Mutation](#122-adaptive-mutation)
    - [Evolution Memory](#123-evolution-memory)
    - [Cross-Pollination](#124-cross-pollination)
13. [Output & Generated APIs](#13-output--generated-apis)
    - [Generated Structure](#131-generated-structure)
    - [Running Generated APIs](#132-running-generated-apis)
    - [Docker Testing](#133-docker-testing)
14. [Customization & Extending](#14-customization--extending)
    - [Adjusting Fitness Weights](#141-adjusting-fitness-weights)
    - [Adding New Services](#142-adding-new-services)
    - [Modifying Mutation Rate](#143-modifying-mutation-rate)
    - [Adding New Genes](#144-adding-new-genes)
15. [Troubleshooting](#15-troubleshooting)
    - [Common Issues](#151-common-issues)
    - [Logs & Debugging](#152-logs--debugging)
    - [Database Issues](#153-database-issues)
    - [WebSocket Connection Issues](#154-websocket-connection-issues)
16. [FAQ](#16-faq)
17. [Glossary](#17-glossary)
18. [API Reference Summary](#18-api-reference-summary)

---

## 1. Overview

The **Autonomous Evolution Engine** applies genetic algorithms to the problem of API architecture design. Instead of hand-crafting microservice architectures, the engine:

1. **Creates random populations** of API architectures (called genomes)
2. **Evaluates each architecture** using a multi-objective fitness function (security, performance, best practices, production readiness)
3. **Selects the best performers** using tournament selection
4. **Breeds new generations** through crossover (mixing parent genes) and mutation (random changes)
5. **Repeats for N generations** until optimal architectures emerge
6. **Generates working code** from the best genome — a complete FastAPI application with all services

The system offers two evolution modes:
- **Standard Evolution** — Classic genetic algorithm with configurable generations and population size
- **Elite Evolution** — Advanced mode with multi-population groups, adaptive mutation, and persistent learning memory

**Example Evolution Run:**

```
Generation 1: Best fitness = 0.452 (random architectures)
Generation 2: Best fitness = 0.578 (improving)
Generation 3: Best fitness = 0.623 (better security)
...
Generation 10: Best fitness = 0.847 (near-optimal)
```

---

## 2. System Requirements

### Minimum Requirements
| Component | Requirement |
|-----------|------------|
| **OS** | Windows 10+, macOS 12+, Linux (any modern distro) |
| **Python** | 3.10 or higher |
| **Node.js** | 18 or higher |
| **RAM** | 512 MB (system only), 2 GB (with frontend) |
| **Disk** | 500 MB free space |

### Recommended
| Component | Recommendation |
|-----------|--------------|
| **RAM** | 4 GB or more |
| **Docker** | Docker Desktop 24+ (for API container testing) |
| **Ollama** | Optional — for LLM-guided mutation features |
| **GPU** | Not required |

### Software Dependencies
- **Backend:** FastAPI, Uvicorn, SQLAlchemy, Pydantic, WebSockets, httpx
- **Frontend:** React 18+, modern web browser (Chrome, Firefox, Edge)
- **Optional:** Docker CLI, Ollama (for LLM features)

---

## 3. Quick Start (5 Minutes)

```bash
# 1. Navigate to the project
cd autonomous-api

# 2. Install backend dependencies
pip install -r requirements.txt
# OR: pip install fastapi uvicorn sqlalchemy pydantic-settings websockets httpx psutil sse-starlette

# 3. Start the backend server
uvicorn app.main:app --reload --port 8000

# 4. Open another terminal, start the frontend
cd reasoning-ui
npm install
npm start

# 5. Open browser to http://localhost:3000
# 6. Click "Start Evolution" — watch it evolve!
```

That's it! Within seconds you'll see generations evolving in real-time.

---

## 4. Installation

### 4.1 Backend Setup

#### Option A: Using requirements.txt (Recommended)
```bash
cd autonomous-api
pip install -r requirements.txt
```

#### Option B: Manual pip install
```bash
cd autonomous-api
pip install fastapi uvicorn[standard] sqlalchemy pydantic-settings websockets httpx psutil sse-starlette
```

#### Option C: Using pyproject.toml
```bash
cd autonomous-api
pip install .
```

#### Option D: Virtual Environment (Recommended for isolation)
```bash
cd autonomous-api
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 4.2 Frontend Setup

```bash
cd reasoning-ui
npm install
```

### 4.3 Docker Setup (Optional)

Docker is optional but enables the system to build and test generated APIs inside containers.

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Ensure Docker is running before using the "Use Docker" option in the dashboard

---

## 5. Configuration

### 5.1 Environment Variables

Copy the example environment file:

```bash
cd autonomous-api
cp .env.example .env
```

Edit `.env` to customize:

```ini
# Application
APP_NAME=Autonomous Evolution Engine
APP_VERSION=3.1.0
DEBUG=false

# Database (SQLite by default — change to PostgreSQL for production)
DATABASE_URL=sqlite:///./evolution.db

# Ollama (for LLM-guided mutation — optional)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# CORS — add your frontend URL here
CORS_ORIGINS=["http://localhost:3000"]

# Security
SECRET_KEY=change-this-in-production
API_KEY_HEADER=X-API-Key
ADMIN_API_KEY=

# Rate Limiting
RATE_LIMIT_GENERAL=100        # requests per window
RATE_LIMIT_EVOLUTION=20       # evolution requests per window
RATE_LIMIT_WINDOW=60          # window in seconds

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### 5.2 CORS Configuration

The CORS_ORIGINS setting controls which frontend URLs can connect to the API:

```ini
# Single frontend
CORS_ORIGINS=["http://localhost:3000"]

# Multiple frontends (production)
CORS_ORIGINS=["http://localhost:3000", "https://myapp.example.com"]

# Development (allow all — not recommended for production)
CORS_ORIGINS=["*"]
```

### 5.3 Rate Limiting

Rate limiting protects the evolution endpoints from abuse:

| Setting | Default | Description |
|---------|---------|-------------|
| `RATE_LIMIT_GENERAL` | 100 | General API requests per window |
| `RATE_LIMIT_EVOLUTION` | 20 | Evolution start requests per window |
| `RATE_LIMIT_WINDOW` | 60 | Window duration in seconds |

Rate limit headers are included in API responses:
- `X-RateLimit-Limit` — Maximum requests allowed
- `X-RateLimit-Remaining` — Remaining requests in current window
- `X-RateLimit-Reset` — Unix timestamp when the window resets

---

## 6. Running the System

### 6.1 Starting the Backend

```bash
cd autonomous-api

# Development mode (auto-reload on code changes)
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# With custom host and port
uvicorn app.main:app --host 0.0.0.0 --port 8080

# With SSL (HTTPS)
uvicorn app.main:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

The backend will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 6.2 Starting the Frontend

```bash
cd reasoning-ui
npm start
```

The frontend will be available at `http://localhost:3000`

> **Note:** The frontend expects the backend at `http://127.0.0.1:8000`. To change this, set `REACT_APP_API_URL` environment variable.

### 6.3 Quick Startup Scripts

The project includes startup scripts:

**Windows (Command Prompt):**
```bash
START_ALL.bat
```

**Windows (PowerShell):**
```powershell
.\START_ALL.ps1
```

**macOS/Linux:**
```bash
./start_all.sh
```

---

## 7. Using the Web Dashboard

### 7.1 Dashboard Overview

When you open `http://localhost:3000`, you'll see the **Evolution Dashboard** with these sections:

1. **Header** — Title, connection status indicator (● Connected / ○ Disconnected)
2. **Configuration Panel** — Evolution parameters and mode selection
3. **Best Genome Panel** — JSON display of the best architecture found
4. **Learning Insights Panel** — Elite mode pattern analysis (Elite mode only)
5. **Fitness History Chart** — Per-generation best and average fitness bars
6. **Event Log** — Color-coded real-time message log

### 7.2 Standard Evolution

1. **Set Generations** (1-100): How many generations to evolve (default: 10)
2. **Set Population Size** (4-50): Number of architectures per generation (default: 10)
3. **Toggle Docker**: Check "Use Docker" to build and test generated APIs in containers (requires Docker)
4. **Ensure Elite Mode is OFF** (default)
5. Click **🚀 Start Evolution**

You'll see real-time updates:
```
12:00:01 🚀 Evolution started: 10 generations
12:00:01 ⏳ Generation 1/10
12:00:02 ✅ Gen 1: Best=0.452, Avg=0.321
12:00:02 🏆 New best genome! Fitness: 0.452
12:00:02 ⏳ Generation 2/10
12:00:03 ✅ Gen 2: Best=0.578, Avg=0.410
...
12:00:10 🔨 Building best genome at: output/generated_api
12:00:11 🎉 Evolution complete!
```

### 7.3 Elite Evolution

Elite mode adds advanced features:

1. **Toggle 🧠 Elite Mode** to ON
2. **Additional options appear:**
   - **Multi-Population System** (default: ON) — 4 specialized groups (balanced, performance, security, operations)
   - **Adaptive Mutation** (default: ON) — Mutation learns from successful patterns
3. Set generations and population size
4. Click **🧬 Start Elite Evolution**

You'll see group-specific updates:
```
12:00:01 🚀 Elite evolution started: 10 generations, Groups: balanced, performance, security, operations
12:00:01 ⏳ Generation 1/10
12:00:02 ✅ [balanced] Gen 1: Best=0.452, Avg=0.321
12:00:02 ✅ [performance] Gen 1: Best=0.611, Avg=0.445
12:00:02 ✅ [security] Gen 1: Best=0.534, Avg=0.398
...
12:00:15 🏆 New global best! Group: operations, Fitness: 0.891
```

After completion, click **📊 Load Insights** to see:
- Best authentication method found
- Best database type found
- Cache and rate limiting impact percentages
- Suggested genome configuration
- Statistics (total runs, average fitness)

### 7.4 Synchronous Quick Test

For a fast test without WebSocket streaming:

1. Configure generations and population size
2. Click **⚡ Quick Test (Sync)**

This runs evolution synchronously and returns all results at once. Useful for testing configuration changes quickly.

### 7.5 Viewing Results

**Best Genome Display:**
Shows the best architecture found as formatted JSON:

```json
{
  "genome_id": "a1b2c3d4",
  "services": ["auth", "users", "payments"],
  "auth": "jwt",
  "database": "postgres",
  "cache_enabled": true,
  "rate_limiting": true,
  "cors_enabled": true,
  "logging_level": "INFO",
  "api_version": "v1"
}
```

**Generated Code:**
The best genome is automatically built into working code at `autonomous-api/output/generated_api/`.

---

## 8. Using the REST API

All API endpoints are documented at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` (ReDoc).

### 8.1 Health Check

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "3.1.0",
  "timestamp": "2026-07-27T01:00:00",
  "components": {
    "database": "healthy",
    "memory": "healthy",
    "disk": "healthy"
  },
  "memory_usage": {
    "rss_mb": 45.23,
    "vms_mb": 120.45,
    "percent": 2.34
  }
}
```

### 8.2 Standard Evolution (Async)

Starts evolution as a background task. Connect to WebSocket for real-time updates.

```bash
curl -X POST http://localhost:8000/evolve/start \
  -H "Content-Type: application/json" \
  -d '{
    "generations": 10,
    "population_size": 10,
    "use_docker": false
  }'
```

**Response:**
```json
{
  "message": "Evolution started",
  "note": "Connect to WebSocket /ws/evolution to receive real-time updates"
}
```

**Parameters:**
| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `generations` | int | 10 | 1-100 | Number of generations to evolve |
| `population_size` | int | 10 | 4-50 | Population size per generation |
| `use_docker` | bool | false | — | Build and test with Docker |

### 8.3 Standard Evolution (Sync)

Runs evolution synchronously (blocking). Returns complete results when done.

```bash
curl -X POST http://localhost:8000/evolve/sync \
  -H "Content-Type: application/json" \
  -d '{"generations": 5, "population_size": 8}'
```

**Response:**
```json
{
  "best_genome": { ... },
  "best_fitness": 0.847,
  "production_readiness": { ... },
  "history": [
    {"generation": 1, "best_score": 0.452, "avg_score": 0.321},
    {"generation": 2, "best_score": 0.578, "avg_score": 0.410},
    ...
  ],
  "output_path": "output/generated_api",
  "total_generations": 5
}
```

### 8.4 Elite Evolution

```bash
curl -X POST http://localhost:8000/evolve/elite/start \
  -H "Content-Type: application/json" \
  -d '{
    "generations": 10,
    "population_size": 8,
    "use_multi_population": true,
    "enable_adaptive_mutation": true,
    "use_docker": false
  }'
```

**Response:**
```json
{
  "message": "Elite evolution started",
  "features": {
    "multi_population": true,
    "adaptive_mutation": true,
    "persistent_memory": true
  }
}
```

### 8.5 Production Readiness Gate

Analyzes a genome against production deployment requirements.

```bash
curl -X POST http://localhost:8000/production/readiness \
  -H "Content-Type: application/json" \
  -d '{
    "genome": {
      "services": ["auth", "users", "payments"],
      "auth": "jwt",
      "database": "postgres",
      "cache_enabled": true,
      "rate_limiting": true,
      "cors_enabled": true,
      "logging_level": "INFO",
      "api_version": "v1"
    },
    "deployment_target": "docker_compose"
  }'
```

**Response:**
```json
{
  "status": "ready",
  "score": 0.912,
  "deployment_target": "docker_compose",
  "blockers": [],
  "warnings": ["CORS must be restricted to explicit production origins at deploy time."],
  "dimensions": [
    {"name": "security", "score": 0.950, "weight": 0.30, "weighted_score": 0.285},
    {"name": "persistence", "score": 1.000, "weight": 0.20, "weighted_score": 0.200},
    ...
  ],
  "recommendations": [...],
  "required_capabilities": ["health_check", "structured_logging", ...]
}
```

**Status Values:**
| Status | Meaning |
|--------|---------|
| `ready` | Score ≥ 0.85, no blockers — safe to deploy |
| `needs_review` | Score ≥ 0.70, no blockers — deploy with caution |
| `not_ready` | Score < 0.70, no blockers — needs improvement |
| `blocked` | Has blockers — must fix before deployment |

### 8.6 Elite Insights & Memory

**Get Learning Insights:**
```bash
curl http://localhost:8000/evolve/elite/insights
```

**Clear Memory:**
```bash
curl -X POST http://localhost:8000/evolve/elite/clear-memory
```

---

## 9. WebSocket Real-Time Updates

Connect to the WebSocket endpoint to receive live evolution events.

### Connection

```javascript
// JavaScript (browser)
const ws = new WebSocket("ws://localhost:8000/ws/evolution");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data);
};
```

```python
# Python
import websockets
import asyncio
import json

async def listen():
    async with websockets.connect("ws://localhost:8000/ws/evolution") as ws:
        async for message in ws:
            data = json.loads(message)
            print(f"[{data['type']}]", data)

asyncio.run(listen())
```

```bash
# Using wscat (npm install -g wscat)
wscat -c ws://localhost:8000/ws/evolution
```

### Event Types

| Event Type | Description | Payload Includes |
|------------|-------------|------------------|
| `evolution_start` | Evolution run begun | run_id, generations, population_size |
| `generation_start` | New generation started | generation, total_generations |
| `generation_complete` | Generation evaluated | best_score, avg_score, fitness_scores |
| `new_best` | New best genome found | fitness, genome (full), generation |
| `building_best` | Code generation started | output_path |
| `docker_test` | Docker test result | success, port, api_working |
| `evolution_complete` | Evolution finished | run_id, result (full) |
| `elite_evolution_start` | Elite evolution begun | groups, adaptive_mutation |
| `new_global_best` | New global best (elite) | group, fitness, genome |
| `group_complete` | Group generation done | group, best_score, avg_score |
| `cross_pollination` | Groups exchanged genes | generation |
| `building_complete` | Build finished | output_path, best_fitness |
| `elite_evolution_complete` | Elite evolution done | result (full) |

---

## 10. Understanding Genomes

### 10.1 Genome Structure

A genome represents the complete DNA of an API architecture:

```json
{
  "genome_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "services": ["auth", "users", "payments", "analytics"],
  "auth": "jwt",
  "database": "postgres",
  "cache_enabled": true,
  "rate_limiting": true,
  "cors_enabled": true,
  "logging_level": "INFO",
  "api_version": "v1",
  "security_score": 1.0,

  "openapi_version": "3.1.0",
  "health_endpoints": true,
  "metrics_endpoints": true,
  "tracing_enabled": true,
  "circuit_breaker": true,
  "retry_policy": {
    "max_attempts": 3,
    "base_delay": 1.0,
    "max_delay": 10.0,
    "backoff_multiplier": 2.0
  },
  "timeout_config": {
    "connect_timeout": 15.0,
    "read_timeout": 30.0,
    "write_timeout": 30.0,
    "request_timeout": 60.0
  },
  "backends": [
    {"type": "cache", "implementation": "redis", "connection_pool_size": 10}
  ],
  "middleware": [
    "auth", "caching", "logging", "rate_limiting", "cors"
  ],
  "security_policies": [
    {"type": "jwt_validation", "algorithm": "RS256", "expiration_minutes": 480}
  ],
  "metrics": {
    "openapi_completeness": 0.85,
    "auth_coverage": 0.92,
    "migration_safety": 0.78,
    "observability_coverage": 0.7,
    "latency_estimate": 350.0,
    "error_budget_estimate": 0.001,
    "dependency_risk": 0.2,
    "cloud_cost_estimate": 320.0,
    "test_coverage_score": 0.6,
    "security_score": 0.9,
    "architecture_complexity": 0.5,
    "performance_score": 0.8
  }
}
```

### 10.2 Genes and Their Meanings

| Gene | Possible Values | Description |
|------|-----------------|-------------|
| `services` | 2-6 from 12 available | Microservices to include (auth, users, payments, analytics, notifications, search, files, admin, products, orders, inventory, reports) |
| `auth` | jwt, oauth2, api_key, basic | Authentication method |
| `database` | postgres, mysql, sqlite | Database backend |
| `cache_enabled` | true/false | Enable Redis/memcached caching |
| `rate_limiting` | true/false | Enable rate limiting |
| `cors_enabled` | true/false | Enable CORS headers |
| `logging_level` | DEBUG, INFO, WARNING, ERROR | Logging verbosity |
| `api_version` | v1, v2, v3 | API version prefix |
| `openapi_version` | 3.0.0, 3.1.0 | OpenAPI spec version |
| `health_endpoints` | true/false | Include /health, /ready endpoints |
| `metrics_endpoints` | true/false | Include Prometheus metrics endpoint |
| `tracing_enabled` | true/false | Enable distributed tracing |
| `circuit_breaker` | true/false | Enable circuit breaker pattern |
| `retry_policy` | object | Retry configuration (attempts, delays) |
| `timeout_config` | object | Timeout configuration (connect, read, write) |

---

## 11. Understanding Fitness Scoring

### 11.1 Fitness Components

The fitness function evaluates genomes across multiple weighted dimensions:

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| **Security** | 15% | Auth method strength, critical service protection, rate limiting, CORS |
| **Architecture** | 10% | Number of services (more = richer, up to 6) |
| **Performance** | 15% | Caching, circuit breaker, tracing |
| **Best Practices** | 10% | Rate limiting, CORS, logging level, health endpoints |
| **Database Quality** | 5% | Postgres (1.0) > MySQL (0.9) > SQLite (0.4) |
| **Production Fitness** | 30% | Comprehensive production metrics (see below) |

**Total maximum possible fitness: ~0.95 (due to trade-offs)**

### 11.2 Production Fitness Scoring

The production fitness scorer evaluates 10 additional dimensions:

| Metric | Weight | Description |
|--------|--------|-------------|
| OpenAPI Completeness | 10% | API documentation quality |
| Auth Coverage | 15% | Authentication coverage across endpoints |
| Migration Safety | 8% | Database migration compatibility |
| Observability | 12% | Metrics, tracing, health checks |
| Latency Estimate | 10% | Estimated response time |
| Error Budget | 10% | Estimated error rate |
| Dependency Risk | 10% | (Inverted) Lower risk = higher score |
| Cloud Cost | 5% | (Inverted) Lower cost = higher score |
| Test Coverage | 10% | Estimated test coverage |
| Security Score | 10% | Overall security posture |

### 11.3 Security Scoring

The security function calculates a base score with penalties and bonuses:

| Condition | Effect |
|-----------|--------|
| JWT auth | No penalty |
| OAuth2 auth | No penalty |
| API Key auth | -0.2 penalty |
| Basic auth | -0.6 penalty |
| Critical services with weak auth | -0.4 penalty |
| Rate limiting enabled | +0.1 bonus |
| CORS disabled | -0.1 penalty |

---

## 12. Elite Mode Features

### 12.1 Multi-Population System

Instead of one population, elite mode maintains 4 specialized groups:

| Group | Focus | Specialization |
|-------|-------|----------------|
| **Balanced** | General purpose | Equal weight across all fitness dimensions |
| **Performance** | Speed | Prioritizes caching, circuit breaker, tracing (60% weight) |
| **Security** | Safety | Prioritizes auth strength, security policies (30% weight) |
| **Operations** | Deployability | Prioritizes production readiness score (60% weight) |

Each group evolves independently with its own fitness weighting, then shares successful traits through cross-pollination.

### 12.2 Adaptive Mutation

Standard mutation uses a fixed 20% mutation rate. Adaptive mutation:

- **Tracks which gene values** lead to higher fitness scores
- **Shifts mutation bias** toward successful patterns over time
- **Learns from history** — after many runs, mutations are guided by accumulated knowledge
- **Reports bias** via the insights endpoint

### 12.3 Evolution Memory

The `EvolutionMemory` system:

- **Records every run** — best genome, worst genome, fitness scores
- **Analyzes patterns** — which auth methods, databases, and features correlate with higher fitness
- **Suggests starting genomes** based on accumulated knowledge
- **Persists across runs** — learning carries over between evolution sessions

### 12.4 Cross-Pollination

Every 3 generations, elite mode performs cross-pollination:

- Top genomes from each group are shared with other groups
- This prevents any group from getting stuck in a local optimum
- Good ideas from the performance group can help the security group and vice versa

---

## 13. Output & Generated APIs

### 13.1 Generated Structure

When evolution completes, the best genome is built into a working FastAPI application at `output/generated_api/`:

```
output/generated_api/
├── main.py              # FastAPI app with all services
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container definition
├── README.md           # API documentation
└── services/
    ├── auth.py         # Authentication service (if selected)
    ├── users.py        # User management (if selected)
    ├── payments.py     # Payment processing (if selected)
    └── ...             # Other selected services
```

### 13.2 Running Generated APIs

```bash
cd output/generated_api
pip install -r requirements.txt
uvicorn main:app --reload
```

Each service provides full CRUD endpoints:
- `GET /api/{version}/{service}/` — List items
- `GET /api/{version}/{service}/{id}` — Get item
- `POST /api/{version}/{service}/` — Create item
- `PUT /api/{version}/{service}/{id}` — Update item
- `DELETE /api/{version}/{service}/{id}` — Delete item

### 13.3 Docker Testing

When "Use Docker" is enabled during evolution:

1. The best genome is built into code
2. A Docker image is built from the generated code
3. A container is launched on a random port (8001-9000)
4. The API health endpoint is tested
5. The container is stopped after testing

Docker testing adds 30-60 seconds per evolution run.

---

## 14. Customization & Extending

### 14.1 Adjusting Fitness Weights

Edit `app/engine/fitness.py`:

```python
# Change weights to prioritize different aspects
fitness += security * 0.40      # Increase security importance (was 0.15)
fitness += architecture * 0.05  # Decrease architecture (was 0.10)
fitness += performance * 0.25   # Increase performance (was 0.15)
```

### 14.2 Adding New Services

Edit `app/engine/genome.py`:

```python
available_services = [
    "auth", "users", "payments", 
    "analytics", "notifications",
    "search", "files", "admin",
    "products", "orders", "inventory", "reports",
    "ml-service", "graphql", "webhooks"  # Add new services here
]
```

Also add the corresponding service generator in `app/engine/builder.py` if needed.

### 14.3 Modifying Mutation Rate

Edit `app/engine/evolution.py`:

```python
# Standard mode
child = mutate(child, mutation_rate=0.3)  # Higher mutation (default 0.2)

# Lower mutation for more stable evolution
child = mutate(child, mutation_rate=0.05)  # Lower mutation (default 0.2)
```

### 14.4 Adding New Genes

1. **Add to Genome class** (`app/engine/genome.py`):
   ```python
   # In __init__:
   self.new_feature = genome_data.get("new_feature", False)  # Default value
   
   # In _generate_random_genome:
   self.new_feature = random.choice([True, False])
   
   # In encode:
   "new_feature": self.new_feature,
   
   # In decode:
   self.new_feature = data.get("new_feature", False)
   ```

2. **Add to crossover** (`app/core/crossover.py`):
   ```python
   child_data["new_feature"] = random.choice([parent1.new_feature, parent2.new_feature])
   ```

3. **Add to mutation** (`app/core/mutation.py`):
   ```python
   if random.random() < mutation_rate:
       genome_data["new_feature"] = not genome_data["new_feature"]
   ```

4. **Add to fitness** (`app/engine/fitness.py`):
   ```python
   if genome.new_feature:
       fitness += 0.05
   ```

---

## 15. Troubleshooting

### 15.1 Common Issues

#### "Connection refused" when accessing the dashboard
- **Cause:** Backend server not running
- **Fix:** Start the backend with `uvicorn app.main:app --reload --port 8000`

#### "ModuleNotFoundError: No module named 'app'"
- **Cause:** Running from wrong directory
- **Fix:** Ensure you're in the `autonomous-api` directory

#### Docker build fails
- **Cause:** Docker not installed or not running
- **Fix:** Install Docker Desktop and ensure it's running, or disable "Use Docker"

#### Slow evolution performance
- **Cause:** Large population size or many generations
- **Fix:** Reduce generations (5-10) and population size (8-10) for testing

#### Frontend shows "Disconnected" constantly
- **Cause:** Backend WebSocket endpoint unreachable
- **Fix:** Check that backend is running. If on a different port, set `REACT_APP_API_URL`

### 15.2 Logs & Debugging

Logs are written to `autonomous-api/logs/app.log` by default.

To see real-time logs:
```bash
cd autonomous-api
tail -f logs/app.log
```

To increase verbosity, set `LOG_LEVEL=DEBUG` in `.env`.

### 15.3 Database Issues

**Reset the database:**
```bash
cd autonomous-api
rm data/evolution.db
# Restart the backend — it will recreate the database
```

**Database is locked (SQLite):**
- SQLite has limited concurrency. Restart the backend.
- For production, switch to PostgreSQL.

### 15.4 WebSocket Connection Issues

**Frontend cannot connect to WebSocket:**
- Ensure CORS origins are configured correctly
- The frontend uses `127.0.0.1:8000` by default — ensure no proxy is interfering
- Check browser console for WebSocket errors

**WebSocket disconnects frequently:**
- Network timeout issues
- Try reducing generations so runs complete faster
- Check for reverse proxy timeout settings

---

## 16. FAQ

**Q: What is a "genome"?**
A: A genome is a complete description of an API architecture — what services it includes, what authentication it uses, what database backend, etc. The engine evolves these genomes across generations.

**Q: How many generations should I use?**
A: 10-20 generations with population size 10-15 is good for most cases. 5 generations is enough for a quick test. 50+ generations is for research-grade optimization.

**Q: What is a good fitness score?**
A: 0.0-0.3 = Poor, 0.3-0.6 = Average, 0.6-0.8 = Good, 0.8-0.95 = Excellent (theoretical maximum is ~0.95 due to inherent trade-offs)

**Q: Does the system actually deploy the generated APIs?**
A: The system generates the code files. Optional Docker testing builds and runs containers. Actual deployment to production is up to you.

**Q: Can I use this for production systems?**
A: The generated code provides a solid starting point but should be reviewed, tested, and hardened before production use.

**Q: How is this different from random API generation?**
A: The genetic algorithm optimizes toward better architectures over successive generations, guided by the fitness function. Random generation has no optimization direction.

**Q: What happens to the evolution memory?**
A: It's stored in memory (not database) and persists for the lifetime of the backend process. Use the "Clear Memory" endpoint to reset it.

**Q: Can I run multiple evolutions at once?**
A: Yes! Each evolution gets a unique run_id. The WebSocket supports per-run channels.

---

## 17. Glossary

| Term | Definition |
|------|------------|
| **Genome** | A complete API architecture specification (the "DNA" of a system) |
| **Gene** | A single architectural attribute (e.g., auth method, database type) |
| **Population** | A collection of genomes at a given generation |
| **Generation** | One iteration of the evolution process |
| **Fitness** | A score (0.0 to 1.0) measuring how "good" an architecture is |
| **Crossover** | Combining genes from two parent genomes to create a child |
| **Mutation** | Randomly changing a gene to introduce variety |
| **Selection** | Choosing the best genomes to be parents of the next generation |
| **Tournament Selection** | Selecting parents by comparing random subsets of the population |
| **Elite Evolution** | Advanced mode with multi-population, adaptive mutation, and memory |
| **Multi-Population** | Multiple specialized groups evolving in parallel |
| **Adaptive Mutation** | Mutation that learns from past successes |
| **Cross-Pollination** | Sharing top genomes between population groups |
| **Production Readiness** | Assessment of how deployable a genome is |
| **Pareto Front** | Set of genomes where no single objective can be improved without harming another |

---

## 18. API Reference Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint |
| `GET` | `/health` | System health check |
| `POST` | `/evolve/start` | Start async evolution |
| `POST` | `/evolve/sync` | Run sync evolution |
| `GET` | `/evolve/runs` | List all runs |
| `GET` | `/evolve/run/{run_id}` | Get run details |
| `POST` | `/evolve/elite/start` | Start elite evolution |
| `GET` | `/evolve/elite/insights` | Get learning insights |
| `POST` | `/evolve/elite/clear-memory` | Clear evolution memory |
| `POST` | `/production/readiness` | Analyze production readiness |
| `WebSocket` | `/ws/evolution` | Real-time updates |
| `WebSocket` | `/ws/evolution/{run_id}` | Per-run updates |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc documentation |

---

## Appendix: Example Workflows

### Workflow 1: Quick Exploration (5 minutes)

```bash
# Start backend
uvicorn app.main:app --reload

# Curl a quick test
curl -X POST http://localhost:8000/evolve/sync \
  -H "Content-Type: application/json" \
  -d '{"generations": 5, "population_size": 8}'

# Check the generated code
ls -la output/generated_api/
```

### Workflow 2: Full Research Run (15 minutes)

1. Open dashboard at `localhost:3000`
2. Set Generations: 20, Population: 15
3. Enable 🧠 Elite Mode
4. Click 🧬 Start Elite Evolution
5. Watch real-time group progress
6. After completion, click 📊 Load Insights
7. Examine best genome and generated code

### Workflow 3: Production Readiness Check (2 minutes)

```bash
# Run production analysis on a genome
curl -X POST http://localhost:8000/production/readiness \
  -H "Content-Type: application/json" \
  -d '{
    "genome": {"services": ["auth","users"], "auth": "jwt", ...},
    "deployment_target": "kubernetes"
  }'
```

---

*Generated by Autonomous Evolution Engine v3.1.0*