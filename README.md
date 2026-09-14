# Tiannara Software Platform

> Autonomous API architecture discovery and evolution through evolutionary search, code generation, and LLM-guided reasoning.

This repository is the **public Tiannara Software Platform**: an experimental engineering system for exploring how API architectures can be generated, evaluated, and evolved rather than designed as a single fixed implementation.

## What it does

The platform combines a FastAPI backend, React interface, evolutionary search, and optional local LLM assistance.

At a high level:

```text
Architecture candidates
        │
        ▼
  Genome / search space
        │
        ▼
 Evolution + mutation ───────► LLM-guided mutation (optional)
        │
        ▼
 Fitness / multi-objective evaluation
        │
        ▼
 Candidate API generation
        │
        ▼
 Results + telemetry in the web UI
```

The goal is not simply to generate boilerplate. The project explores **automated architectural discovery**: searching a design space, evaluating candidate solutions, and retaining useful evolutionary state across runs.

## Core capabilities

- **Evolutionary architecture search** — population-based exploration of API design candidates.
- **Genome-based generation** — candidate architectures can be represented and translated into FastAPI implementations.
- **Multi-objective evaluation** — candidates can be evaluated across multiple architectural dimensions.
- **LLM-guided mutation** — local LLM assistance can inform mutation/search decisions.
- **Persistent evolutionary state** — learning and experiment state can survive individual runs.
- **Interactive observability** — React dashboard with real-time evolution updates and fitness visualisation.
- **API service layer** — FastAPI endpoints for controlling and observing evolution.
- **Operational hardening** — validation, middleware, health/metrics surfaces, and container-oriented execution paths.

## Architecture

```text
┌─────────────────────┐
│     React UI        │
│  reasoning-ui/      │
└──────────┬──────────┘
           │ HTTP / WebSocket
           ▼
┌─────────────────────┐       HTTP        ┌─────────────────────┐
│   FastAPI Backend   │ ◄────────────────►│   Local LLM         │
│   autonomous-api/   │                   │      Ollama         │
└──────────┬──────────┘                   └─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Evolution Engine    │
│ genomes / fitness   │
│ mutation / memory   │
└──────────┬──────────┘
           ▼
      Generated API
```

### Repository layout

```text
.
├── autonomous-api/          # FastAPI backend and evolution engine
│   ├── app/api/             # HTTP API surface
│   ├── app/core/            # Configuration and shared infrastructure
│   ├── app/engine/          # Evolution, genome and mutation logic
│   ├── app/middleware/      # Cross-cutting HTTP/security concerns
│   ├── app/models/          # Persistence/domain models
│   ├── app/storage/         # Storage layer
│   └── tests/               # Backend tests
│
├── reasoning-ui/             # React observability/control interface
├── QUICK_START.md            # Detailed startup instructions
├── STARTUP_FLOW.md           # Startup and architecture notes
└── start_all.*               # Platform startup helpers
```

## Current status

This is a **research/engineering platform**, not a claim of a universally optimal autonomous API designer.

The repository contains a substantial working implementation and experimentation surface, but performance figures, convergence claims, and architectural-quality claims should be interpreted as **benchmark-specific evidence**, not general guarantees. Reproduce the relevant experiment before treating a reported result as independently verified.

## Getting started

### Prerequisites

- Python 3.10+
- Node.js 16+
- Git
- Ollama, when using LLM-guided mutation

### Start the platform

Windows:

```powershell
.\START_ALL.ps1
```

or:

```text
START_ALL.bat
```

Linux/macOS:

```bash
chmod +x start_all.sh
./start_all.sh
```

For the detailed setup path, see [QUICK_START.md](QUICK_START.md).

### Development setup

Backend:

```bash
cd autonomous-api
pip install -r requirements.txt
pytest tests/ -v
```

Frontend:

```bash
cd reasoning-ui
npm install
npm start
```

The exact startup commands and environment requirements should be checked against the current scripts before deployment.

## Local service surfaces

The default development configuration exposes the following surfaces when enabled:

| Surface | Default |
|---|---|
| React UI | `http://localhost:3001` |
| FastAPI | `http://localhost:8000` |
| OpenAPI / Swagger | `http://localhost:8000/docs` |
| Health endpoint | `http://localhost:8000/health` |
| Evolution WebSocket | `ws://localhost:8000/ws/evolution` |
| Metrics | `http://localhost:8000/metrics` |

These are development defaults, not production deployment guarantees.

## Testing

Backend tests:

```bash
cd autonomous-api
pytest tests/ -v
```

Additional performance/load tooling exists in the repository. Treat benchmark output as experiment evidence and preserve the exact configuration when comparing runs.

## Documentation

- [Quick Start](QUICK_START.md)
- [Startup Flow](STARTUP_FLOW.md)
- [Backend technical documentation](autonomous-api/README_COMPLETE.md)
- [Technical reference](autonomous-api/COMPLETE_TECHNICAL_DOCS.md)
- [Architecture rationale](autonomous-api/WHY_THIS_IS_SPECIAL.md)
- [Backend optimisation notes](autonomous-api/BACKEND_OPTIMIZATIONS.md)

## Relationship to Tiannara

The project is part of the broader **Tiannara engineering work** and is presented publicly as the Tiannara Software Platform.

It should not be confused with the private Main Tiannara system. The private system contains additional research and engineering tracks that are intentionally not exposed through this repository.

## Research foundation

The evolutionary-search direction draws on established work in genetic algorithms and multi-objective optimisation, including:

- John Holland — *Adaptation in Natural and Artificial Systems* (1975)
- Kalyanmoy Deb — *Multi-Objective Optimization Using Evolutionary Algorithms* (2001)

LLM-guided search is treated here as an engineering extension to the evolutionary architecture workflow, rather than evidence that the system independently possesses general architectural intelligence.

## Contributing

Issues and pull requests are welcome. When proposing changes, include enough information to reproduce the relevant behaviour, especially for changes to the evolution engine, fitness functions, mutation logic, or generated-code pipeline.

## License

See [LICENSE](LICENSE) for the repository's licensing terms.

---

**Tiannara Software Platform · Kimiti4**
