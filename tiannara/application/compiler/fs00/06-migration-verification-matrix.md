# FS-00 Supplement — Migration and Verification Matrix

**Status:** REVIEW DRAFT — planning artifact only; no code migration authorized  
**Decision dependency:** Proposed FS-00-ADR-001 remains unapproved.  
**Rule:** Preserve the current behavior and fail-closed posture until the reviewer approves the architecture and the FS-01 contract.

## Migration principles

- Do not mutate ISR schema or expand Android semantics during FS-00.
- Keep source ISR, canonical compiler IR, generated repository, runtime instance and evidence as distinct bound objects.
- Do not migrate multiple backend families in one atomic change.
- A test that mocks a toolchain, fabricates an APK, or substitutes synthetic runtime evidence cannot satisfy native build/runtime acceptance.
- Every stage has an explicit stop condition and rollback point. UNKNOWN, missing evidence and unsupported semantics are non-passing outcomes.

## Staged matrix

| Stage | Scope | Preconditions | Required checks | Stop / rollback condition |
|---|---|---|---|---|
| M0 — Freeze baseline | Capture source commit, ISR schema/graph hashes, current plan fixtures, backend manifests, tests and workflow definitions. | Human approves beginning implementation only after FS-00 gate. | Hash manifest; inventory tests; rerun baseline suite in a clean checkout; record exact commands/results. | Any unexplained baseline drift or unavailable required input. No source changes. |
| M1 — Contract fixtures | Add versioned ISR and plan fixtures covering every node type, edge type, typed behavior payload and malformed/unknown kind. | Approved FS-01 contract specifies mapping/unknown policy. | Coverage matrix; deterministic canonical serialization/hash; malformed input and dangling-reference tests; round-trip or semantic-correspondence assertions where applicable. | Any source semantic unaccounted for, silently dropped, or represented ambiguously. |
| M2 — Canonical IR adapter | Introduce canonical IR schema/version and explicit ISR-to-IR mapping alongside existing APIs. | M1 fixtures approved; compatibility plan reviewed. | Mapping completeness; deterministic repeated builds; source-to-IR trace; compatibility tests for current consumers; negative tests for unknown constructs. | Any behavior change without approved migration, unstable hash, or missing lineage. |
| M3 — Core/backend boundary | Make backend implementations consume only canonical IR and declare feature/capability manifests. Move source-bound convenience helpers out of backend modules if approved. | M2 accepted and migration patch plan approved. | Static import-boundary check; registry/plugin conformance; unsupported-feature refusal; backend isolation and malformed manifest tests. | Core imports backend; backend silently accepts unsupported semantics; compatibility regression. |
| M4 — Orchestration seam | Define a production orchestration contract distinct from campaign plan construction and certification runner. | Canonical IR and backend contracts approved. | Input validation; deterministic backend selection; composition of frontend/backend/data/infrastructure artifacts; partial failure quarantine; idempotency/retry tests; lineage completeness. | Partial artifacts published, retry duplicates effects, or missing source binding. |
| M5 — Evidence and independent verification | Bind source, ISR revision, IR, backend/version, candidate, artifacts, build/runtime and verifier results. | M2–M4 stable enough to emit evidence. | Tamper/corruption tests; anti-vacuity tests; independent verifier process; UNKNOWN remains non-pass; secret redaction; verdict-regression tests. | Broken chain or verifier result is trusted without independently checked predicates. |
| M6 — One behavioral vertical slice | Implement only approved ESAP-APP-001 semantics in Android backend and test harness. | FS-00 approved; FS-01/FS-03 contracts approved; real Android SDK/Gradle/emulator available. | Real APK build; emulator install/launch; real UI interactions; behavior oracles; durable-state before/after assertions; process relaunch; offline behavior; negative cases; source-to-runtime lineage. | Any required criterion missing, mocked, flaky without diagnosis, or not bound to the candidate. |
| M7 — Backend-family rollout | Extend one target family at a time after the vertical slice and common contracts are accepted. | M6 passes and backend rollout plan is reviewed. | Per-family feature matrix; native build/run; contract and security tests; negative cases; independent conformance; version matrix. | Capability claimed without evidence or regression against shared semantic fixtures. |
| M8 — Continuous certification | Run supported language/framework/version combinations in CI and recertify changes. | Stable per-family acceptance criteria. | Reproducible CI; dependency update tests; evidence retention; deprecation/unsupported status; regression and rollback drills. | Unsupported combination reported as supported or stale certification presented as current. |

## Minimum test matrix for canonical ISR → IR preservation

| Source construct | Positive coverage | Negative / edge coverage | Required evidence |
|---|---|---|---|
| All declared ISR node kinds | Each kind maps to a documented IR representation or explicit policy-gated non-executable annotation. | Unknown future node kind, missing required payload, invalid behavior payload. | Node coverage report; source and IR hashes; mapping decision per node. |
| All declared ISR edge kinds | Each edge maps to a first-class relation or documented, verified equivalent. | Dangling endpoints, unsupported relation, duplicate/conflicting relation, relation-order variation. | Edge coverage report; relation correspondence assertions. |
| Requirement dependencies/conflicts/refinements/ownership | Semantics retained in the IR and traceability graph. | Conflict unresolved; missing requirement target; ownership ambiguity. | Requirement-to-IR links and conflict-resolution record. |
| Behavior payloads | Payload validation and deterministic canonical form. | Missing/extra/invalid fields, unknown expression/operator, type mismatch. | Validation output and canonical payload hash. |
| Effects, invariants and consequences | Binding and evaluation obligations remain explicit. | Unbound effect, ambiguous target, invariant violation, unsupported consequence. | Binding map, oracle definitions and negative-test output. |
| Frontend routes/interactions | Route, action, target and expected state transition are represented. | Zero/multiple API targets where a single target is required; missing selector; invalid navigation. | Interaction trace and independent expected-state assertions. |
| Security policies | Required policy links preserved and checked against backend capability. | Missing policy, weaker generated policy, unauthorized action. | Policy-version binding and authorization negative tests. |
| Determinism and lineage | Same pinned inputs/config produce equivalent canonical IR and stable declared outputs. | Input order changes, source hash mismatch, modified manifest, stale backend version. | Repeated-run hashes, provenance chain and mismatch diagnostics. |

This matrix is a test-plan proposal, not evidence that these tests currently exist or pass.

## Benchmark-specific acceptance evidence

For ESAP-APP-001, a successful Gradle task or APK file is necessary but insufficient. Evidence must include the exact source revision, approved specification/ISR derivation binding, generated candidate hash, APK hash, emulator/device identity, install and launch results, real UI interaction traces, durable-state assertions across process relaunch, offline behavior, negative cases, and independent semantic-verifier output. Any synthetic or mocked runtime observation must be labelled as such and excluded from certification.

## Rollback and compatibility

- Keep each stage in its own reviewable commit or PR.
- Preserve old entry points while adapters are dual-run only if the approved migration plan explicitly permits this; compare semantic outputs, not just file counts.
- On divergence, stop and retain both reports; do not automatically prefer the new implementation.
- Keep the last known-good source commit and evidence bundle until acceptance is independently reviewed.
- Revert the stage as a unit if tests fail; never “repair” a failure by weakening acceptance criteria.
- Schema/version migration requires separate explicit approval and a migration/rollback fixture set.

## Gate result

**Migration Safety: PARTIAL.** This matrix defines staged gates and stop conditions, but the exact repository-wide import graph, complete consumer inventory, intermediate test commands and rollback commit IDs still require source-driven completion after the ADR is approved. It does not authorize FS-01 or code changes.
