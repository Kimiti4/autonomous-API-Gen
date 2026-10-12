# Ten-Domain Application-Generation Coherence Suite

Status: **SPECIFIED / NOT EXECUTED**

Machine-readable contract: `experiments/compiler-benchmarks/coherence_suite.v1.json`.

## Domains

1. **TaskFlow** — full-stack SaaS, tenancy and RBAC.
2. **Booking** — scheduling, concurrent claims and idempotency.
3. **Commerce** — inventory, order state machines and event delivery.
4. **Wallet/Ledger** — balanced postings, atomic transfers and reconciliation.
5. **Telemetry/Fleet** — bounded event ingestion, identity, ordering and aggregation.
6. **Real-time collaboration** — concurrent edits, authorization, reconnect/replay and backpressure.
7. **Legacy repair** — reproducible defects, minimal fixes and regression preservation.
8. **Production incident** — detect, diagnose, repair safely, verify recovery and prevent recurrence.
9. **Multi-stack equivalence** — identical technology-neutral ISR lowered into materially different stacks with behavior parity.
10. **Enterprise capstone** — integrated identity, cross-service workflows, failure recovery and end-to-end evidence.

## Mandatory protocol

- Exactly two primary iterations per application, one per **distinct end-to-end compiler**. Two targets under the same pipeline do not qualify as two compilers.
- Freeze and hash canonical inputs, reviewed semantic decisions and acceptance criteria before either run.
- Use isolated workspaces, state, credentials and runtime instances.
- Evaluate both outputs with the same independent, versioned acceptance suite.
- Test security, negative cases, data integrity, retries, recovery, reproducibility and requirement-to-artifact-to-test traceability as applicable to the domain.
- Record build/runtime evidence, logs, artifact hashes, intervention history, failures and unrun checks.
- Keep statuses honest: PASS, FAIL, UNKNOWN, BLOCKED or NOT_RUN. Missing, simulated or self-reported evidence is not a PASS; a critical security or integrity failure vetoes the aggregate result.

## Current state

The suite defines domain invariants and negative-case targets; it does not claim the applications have been specified, generated, run or certified. TaskFlow has a canonical problem and acceptance file but remains blocked on trusted semantic review and live compiler integration. The other nine entries need frozen canonical problem specifications and acceptance suites before generation.

Compiler-pair qualification is also still pending. Candidate pipelines must be invoked independently and shown to consume equivalent semantics. A passing schema/preflight test proves only that the declared benchmark contract is structurally coherent; it does not prove runtime behavior.

## Exit gates before app generation

1. Resolve and approve TaskFlow's 15 mandatory semantic fields with source-bound evidence.
2. Verify the trusted evidence envelope against exact snapshot, graph and resolution hashes.
3. Wire that verified envelope through the live compiler orchestration path.
4. Prove field-by-field downstream consumption or fail closed on unsupported semantics.
5. Qualify two materially different end-to-end compiler pipelines.
6. Freeze independent TaskFlow acceptance tests, including the listed negative cases.
7. Run isolated A/B generations, collect evidence, and report every result honestly.
8. Only after TaskFlow's execution/evidence boundaries are sound, freeze the other nine specifications and run their paired trials.

The coherence suite is designed to measure correctness and coherence, not visual polish or the number of generated demo screens.
