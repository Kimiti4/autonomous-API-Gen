# Capability Boundary — Fullstack Certification & Evolution

**Domain:** CBC-1 certification / governed self-repair
**Status:** Documented boundary (not a defect, not a backlog item)

## Scope of today's capability

The Crown Bakery corpus is entirely **backend** workloads:

- 13 categories, 39 intents — all backend runtime intents
- eligible behavioral backends: `python-fastapi` (17 files / artifact
  `58a9737d…`), `rust-axum` (16 files / artifact `15988521…`)
- no frontend/fullstack markers anywhere in the corpus or registry

The certification pipeline certifies a **backend container image** that is
compiled from the same ISR under an alternate eligible backend when governed
evolution is justified (backend-variant self-repair).

## What is out of scope

- Web / SPA / mobile client generation
- UI-framework integration and frontend behavioral probing
- fullstack deployment topologies (bundled frontend + backend)
- frontend artifact novelty (there is no frontend artifact)

## Why it is a *boundary*, not a failure

The ISR/requirements graph contains no UI primitives, so the lowering pipeline
cannot synthesize a frontend — exactly as it cannot synthesize a mobile app or
a database engine.  Certification certifies what the workload actually
requires; a workload with no UI requirement has no UI to certify.

## What happens when fullstack arrives

The governed self-repair surface is already generic:

```
FailureClassification → LearningSignal → EvolutionDecision → EvolutionCandidate
```

A future `frontend_swap` / `fullstack_topology` variant kind plugs into the
same `EvolutionCandidate` mechanism (see
`certification/feedback/candidate.py::VARIANT_KIND_*`) with **no redesign of
the evolution engine**.  The gate set stays identical; only the eligible
artifact classes grow.

## Evidence

- `certification/corpus/corpus.py` — categories/intents (all backend)
- `compiler/composition.py` — backend registry (2 behavioral backends)
- `compiler/core/*` — backend artifact compile (no frontend lowering)
- `docs/evolution/BACKEND_VARIANT_EVOLUTION.md` §12