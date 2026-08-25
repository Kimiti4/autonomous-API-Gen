# ADR-011: Evolution Engine (v1.3)

## Status

Accepted

## Context

v1.2 established the ISR as the sole architectural source of truth and the Genesis Protocol as the deterministic entry point. v1.3 adds the Evolution Engine: a constructive pipeline that explores the architectural decision space under constitutional governance, operating exclusively on the ISR.

## Decision

The Evolution Engine is a staged, Protocol-based pipeline with the following stages:

1. **Construct** — derive a Genome (decision-space representation) from an ISR revision
2. **Evaluate Fitness** — score the ISR+Genome against typed FitnessDimensions
3. **Mutate** — vary gene values within a DecisionSpace (genome-level, no ISR mutation)
4. **Crossover** — recombine two parent genomes (uniform gene-wise)
5. **Select** — Pareto-optimal non-dominated sort + crowding distance
6. **Materialize** — convert a genome back into a valid ISRGraph (ADR-008 compliant)
7. **Refine** — feedback-driven gene value updates for weak fitness dimensions

### Key invariants

- E0: All artifacts declared in `release/poc-v1.3-manifest.lst` exist
- E1: `genome_content_hash` is deterministic and order-independent
- E2: Constructed genome has all required chromosome families
- E3: Mutation only produces values within the DecisionSpace
- E4: Crossover produces a valid genome from two parents
- E5: Pareto sort correctly identifies non-dominated vectors
- E6: Genome lineage is traceable via `OperationRecord`
- E7: Materialized ISRGraph passes ADR-008 invariants
- E8: All pipeline stage classes are Protocol-based (replaceable)
- E9: Selection chooses a Pareto-optimal candidate
- E10: Full pipeline composes correctly end-to-end
- E11: Reference adapters implement their Protocol interfaces

### Architecture

```
evolution/core/           ← ADR-011 engine (genome, fitness, operations, materialize)
evolution/ports/          ← technology-independent seams (OperationalFeedback)
evolution/                ← legacy SelfEvolutionEngine (untouched)
```

The new `evolution/core/` subpackage operates on typed `ISRGraph`/`ISRRevision` objects (not dict payloads). It is orthogonal to the existing `SelfEvolutionEngine` which operates on `CandidateArchitecture` dicts.

### Port: OperationalFeedback

`evolution/ports/feedback.py` defines the `OperationalFeedback` protocol — a technology-independent seam for collecting runtime telemetry (latency, incidents, resource usage). Adapters implement this for Prometheus, Datadog, log aggregation, etc. The reference adapter is `ReferenceOperationalFeedback` (in-memory, for tests).

## Consequences

- All pipeline stages are Protocol-based and independently replaceable
- Reference implementations are deterministic (seeded RNG)
- The ISR is the sole source of truth — genomes are a decision-space abstraction that maps back to valid ISR graphs
- No infrastructure or storage technology is imported into `evolution/core/`
