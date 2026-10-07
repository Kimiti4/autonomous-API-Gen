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

## Existing code that is not yet equivalent to a production target

| Implementation | Language | Current state | Required work |
|---|---|---|---|
| `compiler/backends/rust_axum.py` | Rust | Existing legacy compiler backend | Adapt to typed ProjectCompiler contract, capability declaration, build profile, independent runtime verification |
| `compiler/backends/python_fastapi.py` | Python | Existing legacy/reference backend | Keep separate from the typed FastAPI backend until equivalence/provenance semantics are reconciled |
| production backend modules | mixed | Infrastructure/realization compilers | Do not treat these as application-language targets |

## Expansion order

### Backend 3 — Rust + Axum

Reason: materially different compilation model from Python and Go while an
existing emitter already exists. The first task is an adapter/rewrite against
the typed `SystemModel` contract, not simply registering the legacy emitter.

Required gates:

- typed ISR/SystemModel consumption
- capability declaration
- backend-supplied build profile
- `cargo check` / `cargo test`
- runtime health verification
- generated artifact provenance
- no source/template dependency on Python or Go output
- TaskFlow semantic negative-case coverage where the backend claims support

### Backend 4 — TypeScript + NestJS

Reason: tests a typed managed-runtime ecosystem and a substantially different
package/build model.

Required before implementation is accepted:

- deterministic dependency strategy
- reproducible install/build
- independent runtime verifier
- capability declaration
- explicit unsupported/partial semantics

### Backend 5 — Java + Spring Boot

Reason: exercises a large enterprise ecosystem and JVM compilation model.

### Backend 6 — C# + ASP.NET Core

Reason: exercises the .NET compiler/runtime ecosystem and a distinct deployment
model.

### Backend 7 — Elixir + Phoenix

Reason: tests the BEAM/concurrent-process execution model and is especially
valuable for concurrency-heavy applications such as Booking and real-time
collaboration.

### Backend 8 — Kotlin + Ktor

Reason: JVM alternative with a materially different application/runtime style
from Spring.

## Rules for every new backend

1. The ISR remains authoritative.
2. Backend selection cannot mutate requirements.
3. A backend must explicitly declare supported, partial, and unsupported
   semantic capabilities.
4. Unsupported requirements cause rejection or bounded degradation; they cannot
   silently disappear.
5. Generated code from another backend is never a generator input.
6. Recorded transcripts are regression fixtures, never live-generation evidence.
7. Static checks do not substitute for runtime verification.
8. Simulated runtime observations cannot be certified as production/runtime
   evidence.
9. Each backend receives its own build/test/runtime verification.
10. Cross-backend equivalence compares semantic obligations, not source shape.
11. Backend-specific repairs must preserve the original ISR and be traced.
12. Generation stops when the required scope is certified; no feature expansion
    is allowed merely because a backend can provide it.

## Application progression

Backend diversity will be exercised against increasingly different applications:

- TaskFlow — tenancy, RBAC, audit/effects, lifecycle
- Booking — concurrency, temporal constraints, idempotency
- Commerce — inventory and workflow invariants
- Wallet/Ledger — atomicity, numerical correctness, reconciliation
- Telemetry/Fleet — event ingestion and operational workloads
- Real-time collaboration — concurrency and streaming
- Legacy repair — reverse engineering and minimal-change maintenance
- Production incident — observation, diagnosis, repair, regression verification

The goal is not to maximize the number of language emitters. The goal is to
measure whether one semantic compiler can preserve the same obligations across
different implementation ecosystems.
