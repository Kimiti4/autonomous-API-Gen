# ADR-013 — Compiler Behavioral Certification (CBC-1)

## Status

Proposed (pending certification)

## Context

C0–C11 prove the compiler *substrate* (deterministic lowering, backend isolation, structural conformance). But "a repository that merely contains the expected files is not a successfully generated application." The objective is stronger: **every backend can generate complete, functional software**, proven by execution, at scale, with immutable evidence and an independent verifier.

## Decision

### Certification Trial

One `(intent → ISR → backend)` execution producing an immutable `Trial` record.

### Trial pipeline

structural → semantic → build → test → deploy → runtime → destroy → verify, each a replaceable port with a reference Docker implementation.

### Backend Certification

structural ∧ semantic ∧ compilation ∧ test ∧ deployment ∧ runtime ∧ destruction ∧ evidence-present ∧ independent-verify. No single stage may certify the whole.

### Independence

The verifier runs in a **separate process** and re-derives conformance from the published repo + plan hash; the generator never certifies its own claims.

### Corpus-driven, not demo-driven

Workloads come from a pre-registered corpus across the 13 categories, with explicit novelty classes (template / architectural / novel-intent) reported separately.

### Metrics in four classes

- **Compiler correctness** — structural conformance, repo file count
- **Functional correctness** — tests passed
- **Engineering quality** — deterministic output, independent verification
- **Operational correctness** — build/deploy/runtime/destroy success
- **ISR semantic conformance** — headline metric (1.0 if structural passes, 0.0 otherwise)

### Continuous evolution

Trial failures feed a failure taxonomy → ISR-level feedback (never arbitrary code patches).

## Gate suite (B0–B9)

| Gate | Description |
|------|-------------|
| B0 | Inventory — all manifest artifacts present |
| B1 | Trial model + verdict composition correct |
| B2 | Stage protocols enforceable |
| B7 | Full verdict = all 8 required stages ∧ evidence |
| B8 | Metrics four-class present; ISR semantic conformance headline |
| B9 | Campaign aggregates success matrix + failure taxonomy |
| B-corpus | Default corpus covers all 13 categories |
| B-full-trial | Full stub trial produces CERTIFIED verdict |
| B-verify | Independent verifier (separate process) agrees |
| B-independence | Certification package is pipeline-only |

## Consequences

- Docker-based stages require a container runtime in CI; heavy but necessary for behavioral proof.
- Reference metrics are simple now; richer lint/complexity/maintainability signals are incremental CBC-1 work.
- Scale (thousands of trials) is a campaign-runtime concern, not a substrate concern; the substrate must be correct first.
- The three-campaign progression (substrate validation → scale → novelty) ensures credibility before autonomy.
