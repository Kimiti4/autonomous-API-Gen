# ADR-012 — Compiler Backend System (v1.4)

## Status

Proposed (pending certification)

## Context

The compiler must support multiple backend plugins (Python/FastAPI, Rust/Axum, Go/Fiber, etc.) without the core assuming any language or directory convention. The previous conformance design (`SemanticConformanceChecker.expected_paths`) was Python-layout-specific, violating the plugin boundary.

## Decision

### Backend-agnostic conformance

`ConformanceChecker.check(plan, element_paths, repo)` receives the backend's own `element_paths(plan)` mapping. The core never assumes a file layout; it only verifies coverage + presence.

### CompilerBackend protocol

Every backend implements:
- `element_paths(plan) -> dict[str,str]` — plan element ID → file path
- `compile(plan) -> GeneratedRepository` — emit all files
- `conformance(plan, repo) -> ConformanceReport` — delegate to `CHECKER`

### ISR lowering

`isr_to_plan(revision)` converts an `ISRRevision` graph into a `CompilationPlan` with services, data models, events, and security policies. The lowering traverses the ISR graph taxonomy (SERVICE, DATA_MODEL, EVENT, SECURITY_POLICY nodes; PERSISTS, PUBLISHES, CONSUMED_BY, SECURED_BY edges).

### GeneratedRepository

`build_repository(files)` deterministically hashes sorted `(path, content)` pairs to produce a content-addressed `GeneratedRepository`.

### Two reference backends

1. **PythonFastAPIBackend** — `app/application/*.py`, `app/domain/*.py`, `app/events/*.py`, `app/core/security.py`
2. **RustAxumBackend** — `src/application/*.rs`, `src/domain/*.rs`, `src/events/*.rs`, `src/core/security.rs` + `Cargo.toml`

Both compile the same plan, pass the same backend-agnostic conformance checker, and produce distinct repository hashes.

## Gate suite (C0–C11)

| Gate | Description |
|------|-------------|
| C0 | Inventory — all manifest artifacts present |
| C1 | ISR-to-plan lowering produces services, data models, events, security policies |
| C2 | Plan element IDs include infra stubs (docker, k8s, ci, readme, main, repositories, docs) |
| C3 | PythonFastAPIBackend compiles and conforms |
| C4 | RustAxumBackend compiles and conforms |
| C5 | Compile determinism — same plan → same hash |
| C6 | Distinct backends produce distinct repositories |
| C7 | Omission detected — removing a file fails conformance |
| C8 | Unmapped element detected — empty element_paths fails conformance |
| C9 | Registry lookup by name |
| C10 | Both backends conform and produce distinct output |
| C11 | Compiler core does not import concrete backends (static scan) |

## Consequences

- Adding a new backend (Go Fiber, Spring, NestJS) = new plugin file implementing `element_paths` + `compile` + `conformance`. Zero core changes.
- The plugin boundary is proven by two materially different ecosystems (Python vs Rust) sharing the same plan and conformance checker.
- Structural conformance (this phase) ≠ behavioral conformance (CBC-1 campaign).
