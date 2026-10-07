# ESAP Multi-Backend Compiler Expansion Matrix

## Purpose

Expand ESAP's compiler portfolio so the same technology-neutral ISR can be lowered
into materially different languages, runtimes, frameworks, and deployment models.

A backend is not considered available merely because a source emitter exists.
It becomes a production compiler target only after it satisfies the typed backend
contract and passes independent generation, build, test, runtime, provenance,
and evidence gates.

## Current integrated targets

| Backend | Language | Runtime/framework | Status |
|---|---|---|---|
| `fastapi_hexagonal` | Python | FastAPI | Integrated |
| `go_hexagonal` | Go | stdlib net/http | Integrated; cross-language proof target |

## Expansion order

### Backend 3 — Rust + Axum

An existing Rust/Axum emitter is present in the legacy compiler path. It must be
adapted to the typed SystemModel/backend contract before registration.

Required gates:

- typed ISR/SystemModel consumption
- capability declaration
- backend-supplied build profile
- cargo check/build/test
- runtime health verification
- generated artifact provenance
- no source/template dependency on Python or Go output
- TaskFlow semantic negative-case coverage where the backend claims support

### Backend 4 — TypeScript + NestJS

Tests a typed managed-runtime ecosystem and a substantially different package/build
model.

### Backend 5 — Java + Spring Boot

Exercises a large enterprise ecosystem and JVM compilation model.

### Backend 6 — C# + ASP.NET Core

Exercises the .NET compiler/runtime ecosystem.

### Backend 7 — Elixir + Phoenix

Exercises the BEAM/concurrent-process execution model and is especially valuable
for Booking and real-time collaboration.

### Backend 8 — Kotlin + Ktor

Exercises a JVM alternative with a different application/runtime style from Spring.

### Backend 9 — Angular frontend

Angular is included as a **frontend compiler target**, not a backend service
target. It must consume the same technology-neutral application/API contract and
be independently verifiable.

Required Angular gates:

- generated TypeScript/Angular project
- standalone component/module architecture chosen from ISR
- API contract compatibility with independently generated backend
- `ng build` and unit/component tests
- runtime browser smoke verification
- accessibility/security checks appropriate to the generated UI
- no backend source used as a frontend template
- traceability from UI obligations to ISR capabilities

Angular is therefore evaluated alongside React/Next-style frontend targets when
ESAP reaches frontend-only and full-stack generation experiments.

## Rules for every new backend/compiler

1. The ISR remains authoritative.
2. Backend/compiler selection cannot mutate requirements.
3. A compiler must explicitly declare supported, partial, and unsupported
   semantic capabilities.
4. Unsupported requirements cause rejection or bounded degradation; they cannot
   silently disappear.
5. Generated code from another compiler is never a generator input.
6. Recorded transcripts are regression fixtures, never live-generation evidence.
7. Static checks do not substitute for runtime verification.
8. Simulated runtime observations cannot be certified as real evidence.
9. Each compiler receives its own build/test/runtime verification.
10. Cross-compiler equivalence compares semantic obligations, not source shape.
11. Compiler-specific repairs must preserve the original ISR and be traced.
12. Generation stops when required scope is certified; compiler capabilities must
    not create feature creep.

## Application progression

- TaskFlow — tenancy, RBAC, audit/effects, lifecycle
- Booking — concurrency, temporal constraints, idempotency
- Commerce — inventory and workflow invariants
- Wallet/Ledger — atomicity, numerical correctness, reconciliation
- Telemetry/Fleet — event ingestion and operational workloads
- Real-time collaboration — concurrency and streaming
- Legacy repair — reverse engineering and minimal-change maintenance
- Production incident — observation, diagnosis, repair, regression verification

The objective is not to maximize the number of language emitters. It is to measure
whether one semantic compiler preserves the same obligations across different
implementation ecosystems.
