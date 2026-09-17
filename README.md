# Tiannara Software Platform

> An experimental autonomous software compiler for discovering, evaluating, lowering, generating, and verifying API architectures.

This repository is the **public Tiannara Software Platform**: an engineering system for exploring how software architectures can be represented, searched, evolved, compiled into implementations, and verified against explicit evidence.

The project is moving from a framework-specific API generator toward a **backend-oriented compiler architecture**. The architectural source of truth remains the architecture/Genome representation; implementation technologies are compiler targets rather than requirements of the core model.

## What it does

The platform combines evolutionary search, architecture/genome modeling, capability contracts, compiler backend selection, code generation, runtime verification, and an interactive React control surface.

At a high level:

```text
Requirements / architecture intent
                │
                ▼
        Architecture / Genome
                │
                ▼
      Capability semantics
                │
                ▼
       Compilation Request
                │
                ▼
        Backend Registry
                │
        ┌───────┴────────┐
        ▼                ▼
 python-fastapi     future backends
        │
        ▼
   Generated artifact
        │
        ▼
 Static evidence + runtime verification
        │
        ▼
 Fitness / evolutionary feedback
```

The objective is not simply to generate boilerplate. The project explores **automated architectural discovery and compilation**: searching a design space, evaluating candidate architectures, translating semantic capabilities through an explicit backend boundary, and retaining evidence about what was actually generated and verified.

## Compiler architecture

The current architecture deliberately separates semantic intent from implementation technology.

### Architectural source of truth

The architecture/Genome describes the candidate system. The compiler boundary validates its schema before lowering. Backend implementations are not permitted to silently redefine or mutate the architecture.

### Capability semantics

Capabilities are represented as backend-neutral semantic intent before code generation. A capability can be:

- **requested** — the architecture asks for it;
- **implemented** — the current compiler knows how to lower it;
- **verified** — evidence demonstrates that the generated artifact provides it;
- **certified** — the complete required evidence and runtime gates have passed.

Unsupported or unmapped capabilities remain explicit rather than being silently treated as implemented.

### Backend boundary

Compiler backend selection is explicit. The current concrete backend is `python-fastapi`.

```text
Architecture / Genome
        │
        ▼
CapabilityPlan
        │
        ▼
CompilationRequest
        │
        ▼
CompilerBackend registry
        │
        ▼
Python FastAPI lowering
        │
        ▼
CompiledArtifact
```

The backend-neutral layers intentionally do not depend on FastAPI syntax. This boundary is the foundation for adding additional language/framework targets without changing the architectural model.

A second production backend has **not** been claimed yet; backend neutrality is treated as an architectural contract that still requires independent implementation proof.

## Evolution and verification

Candidate architectures can be explored through evolutionary search and evaluated using explicit fitness/capability evidence.

The verification path distinguishes generation from proof:

```text
Candidate
   │
   ▼
Compile
   │
   ▼
Artifact evidence
   │
   ▼
Runtime probes
   │
   ▼
Capability evidence
   │
   ▼
Fitness / acceptance gates
```

Runtime-required capabilities are not considered verified merely because corresponding configuration or generated fields exist. Where applicable, certification uses real runtime/container execution rather than relying only on static inspection.

## Current implemented capability examples

The compiler currently has end-to-end implementations and verification paths for capabilities including:

- API services and CRUD generation
- API-key, Basic, and JWT authentication paths
- health and OpenAPI surfaces
- CORS
- metrics
- tracing
- rate limiting
- timeout configuration
- retry policy
- circuit breaker
- process-local response caching

Some capabilities remain intentionally **unmapped/unverified**, including the generic `backends` capability itself. This is deliberate: the compiler does not convert an unsupported request into a false positive.

### Important scope distinctions

- The response cache is process-local; it is not evidence of distributed Redis/Memcached semantics.
- The circuit breaker is process-local; it is not evidence of fleet-wide shared breaker state.
- LLM-assisted mutation is optional and does not by itself constitute evidence of autonomous general software-engineering intelligence.
- Benchmark and fitness results are experiment-specific and should not be interpreted as universal guarantees.

## Core capabilities

- **Evolutionary architecture search** — population-based exploration of API design candidates.
- **Genome-based representation** — candidate architectures are represented independently of generated implementation files.
- **Capability contracts** — requested capabilities have explicit implementation status and fail-closed semantics.
- **Semantic capability planning** — capability intent is separated from backend-specific rendering.
- **Backend registry** — compilation targets are selected explicitly rather than inferred from generated text.
- **Multi-objective evaluation** — candidates can be evaluated across multiple architectural dimensions.
- **Runtime verification** — runtime-required capabilities are tested against generated systems.
- **Persistent evolutionary state** — experiment and evolutionary state can survive individual runs.
- **Interactive observability** — React dashboard for evolution and fitness information.
- **Operational hardening** — validation, health/metrics surfaces, rate limiting, retry, circuit breaking, caching, tracing, and container-oriented execution paths.

## Repository layout

```text
.
├── autonomous-api/          # Compiler, API backend, evolution engine and tests
│   ├── app/api/             # HTTP API surface
│   ├── app/core/            # Configuration and shared infrastructure
│   ├── app/engine/          # Genome, semantics, compiler backends and evolution
│   ├── app/middleware/      # Generated/runtime middleware implementations
│   ├── app/models/          # Persistence/domain models
│   ├── app/storage/         # Storage layer
│   └── tests/               # Backend, compiler and verification tests
│
├── reasoning-ui/             # React observability/control interface
├── QUICK_START.md            # Detailed startup instructions
├── STARTUP_FLOW.md           # Startup and architecture notes
└── start_all.*               # Platform startup helpers
```

## Current status

This is a **research/engineering platform**, not a claim of a universally optimal autonomous software designer.

The repository contains a substantial working implementation and an evolving compiler architecture. Current work is focused on strengthening the separation between:

1. architecture representation;
2. capability semantics;
3. backend selection;
4. technology-specific lowering;
5. artifact evidence; and
6. runtime verification.

The `python-fastapi` target is the current concrete compiler backend. Backend-neutral contracts and capability planning are being hardened before introducing another language/framework backend.

Performance figures, convergence claims, and architectural-quality claims should be interpreted as **benchmark- or gate-specific evidence**, not general guarantees. Reproduce the relevant experiment before treating a reported result as independently verified.

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

## Testing and acceptance

Backend tests:

```bash
cd autonomous-api
pytest tests/ -v
```

The repository also contains capability, compiler-boundary, artifact-evidence, runtime, Docker, lint, security, and release-gate checks.

The important acceptance principle is:

> **Green configuration is not the same as verified capability.**

A capability should only advance through the lifecycle when its required contract, artifact, runtime, and certification evidence has been satisfied. CI is the authoritative acceptance surface for repository-level gates.

## Documentation

- [Quick Start](QUICK_START.md)
- [Startup Flow](STARTUP_FLOW.md)
- [Backend technical documentation](autonomous-api/README_COMPLETE.md)
- [Technical reference](autonomous-api/COMPLETE_TECHNICAL_DOCS.md)
- [Architecture rationale](autonomous-api/WHY_THIS_IS_SPECIAL.md)
- [Backend optimisation notes](autonomous-api/BACKEND_OPTIMIZATIONS.md)

## Design principles

### 1. Architecture before implementation

The compiler should reason about architecture and requirements before selecting implementation technologies.

### 2. Technology neutrality at the core

Languages, frameworks, databases, and deployment systems are compiler targets. They should not leak into the architectural representation or semantic capability layer without an explicit boundary.

### 3. Evidence before confidence

Generated code, configuration fields, or successful construction are not sufficient proof of runtime behavior. Verification must match the capability being claimed.

### 4. Fail closed

Unknown architecture fields, unsupported backend targets, and unmapped capabilities should produce explicit failures or explicit unverified states rather than silently degrading into apparent success.

### 5. Evolution without false capability

Evolutionary search is useful only when candidate fitness reflects capabilities the candidate actually implements and verifies.

### 6. Incremental compiler evolution

The system should strengthen contracts and boundaries before adding additional implementation targets. Each new backend should provide independent proof that the abstraction is real rather than merely theoretical.

## Relationship to Tiannara

The project is part of the broader **Tiannara engineering work** and is presented publicly as the Tiannara Software Platform.

It should not be confused with the private Main Tiannara system. The private system contains additional research and engineering tracks that are intentionally not exposed through this repository.

## Research foundation

The evolutionary-search direction draws on established work in genetic algorithms and multi-objective optimisation, including:

- John Holland — *Adaptation in Natural and Artificial Systems* (1975)
- Kalyanmoy Deb — *Multi-Objective Optimization Using Evolutionary Algorithms* (2001)

LLM-guided search is treated here as an engineering extension to the evolutionary architecture workflow, rather than evidence that the system independently possesses general architectural intelligence.

## Contributing

Issues and pull requests are welcome. When proposing changes, include enough information to reproduce the relevant behaviour, especially for changes to the architecture model, compiler boundary, evolution engine, fitness functions, mutation logic, generated-code pipeline, or verification evidence.

## License

See [LICENSE](LICENSE) for the repository's licensing terms.

---

**Tiannara Software Platform · Kimiti4**
