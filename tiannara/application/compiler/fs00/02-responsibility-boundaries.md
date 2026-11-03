# FS-00 Deliverable 2 — Responsibility Boundaries

**Status:** REVIEW DRAFT — not an FS-00 pass or authorization for FS-01  
**Source commit:** `68696e2a07595fed98a19e24ee96c3e4e0e5bfeb`  
**Companion:** `tiannara/application/compiler/fs00/01-existing-architecture-map.md`

## 1. Boundary principle

Each architectural concern must have exactly one accountable owner. Multiple modules may participate, but only one is the authority for the concern's contract. When current code has no defensible owner, record a gap; do not infer ownership from folder names alone.

## 2. Concern-to-owner matrix

| Concern | Proposed authoritative owner | Inputs → outputs | Failure / unknown behavior required | Verification | Evidence |
|---|---|---|---|---|---|
| Constitutional rules and authorization to change architecture | `constitutional_architecture/` governance surfaces; exact authority registry must be confirmed | approved rules/decisions → policy decisions | deny or escalate when authority/signature/state is unknown | governance invariant and unauthorized-transition tests | decision ID, approver, policy version |
| ISR schema and semantic source of truth | `isr/core/` plus its canonical constitutional contract | graph + identity/provenance → validated ISRRevision | reject invalid/unknown semantics, dangling references and invalid hash | schema, graph, invariant, hash checks | schema ID/version, canonical hash, validation report |
| Requirement intelligence and requirement graph | `tiannara/application/intent/`, `tiannara/application/cap_a_*`, and `reqgraph/` where present | user intent + constraints → requirement graph | ambiguity/conflict must be represented or escalated, not silently guessed | requirement coverage/conflict/oracle tests | input reference, graph hash, resolution log |
| Evolution candidate construction and selection | `evolution/` and `tiannara/application/evolution/` | validated ISR/decision space → candidate/genome/fitness/lineage | reject invalid candidates; never self-authorize protected mutations | invariants, mutation bounds, selection reproducibility | parent/candidate hashes, operators, fitness evidence |
| ISR → Compiler IR lowering | `compiler/core/lowering.py` | validated ISRRevision → CompilationPlan | fail closed for semantic loss, ambiguity or unknown nodes | deterministic mapping and semantic correspondence checks | source hash, IR hash, mapping report |
| Canonical Compiler IR contract | **No fully demonstrated owner yet**; current stabilization carrier is `compiler/core/plan.py` | ISR-derived semantic graph → backend-neutral IR | unrepresentable semantics block lowering | schema completeness, canonicalization and coverage checks | IR schema/version/hash |
| Backend protocol and registry | `compiler/core/protocol.py`, `compiler/core/registry.py` | IR + selected backend → generated repository | capability mismatch rejects before emission | protocol conformance and capability-gate tests | backend identity/version and capability manifest |
| Backend-family emission | `compiler/backends/<family>/` | backend-neutral IR → target artifacts | unsupported semantic obligations refuse generation | native build + behavior + negative-case suite | source/plan/repository hashes, build logs |
| Full-stack orchestration | **Gap / not demonstrated as one canonical orchestrator**; campaign runner is certification execution, not automatically compiler orchestration | ISR + backend policy → coherent multi-family candidate | partial composition quarantined; no artifact publication on failed stage | full-stack vertical slice and fault injection | orchestration trace and artifact manifest |
| Verification and semantic conformance | `compiler/core/conformance.py`, `certification/stages/`, and independent verifier surfaces; exact precedence needs reconciliation | candidate + bound inputs → conformance/verification result | UNKNOWN is not PASS; corrupted/missing evidence blocks | independent semantic, build, runtime, security and negative tests | raw results, verifier identity, input/output hashes |
| Certification verdict and governance registry | `certification/governance/` and campaign/decision modules | evidence bundle → verdict and governed record | conflicting or regressed verdict blocks certification | registry regression, anti-vacuity and verdict-policy tests | verdict, phase/attempt ID, evidence refs |
| Evidence, provenance and lineage | `certification/evidence/`, `certification/provenance/`, and `tiannara/application/provenance/` | requirement→ISR→IR→artifact→deployment refs → verifiable chain | missing link/corrupt hash quarantines; secrets redacted | chain verification and lineage completeness | append-only event/manifest/hash chain |
| Execution and deployment infrastructure | `tiannara/infrastructure/`, deployment/runtime-specific backend modules | verified artifact + target → deployed instance/observations | fail/rollback must be explicit; no false deployment success | isolated execution, health checks, rollback and runtime smoke | environment, run ID, deployment ID, logs |
| Learning and knowledge retention | `learning/`, `knowledge/`, `tiannara/application/learning/` | verified observations/evidence → bounded knowledge updates | unverified observations cannot become authoritative facts | provenance validation and regression/replay | evidence source, confidence/status, update record |
| Generated applications and fixtures | `generated/`, `autonomous-api/`, and other explicit generated targets | generated repository/artifacts → runtime instance | never treat fixtures or templates as proof of compiler correctness | candidate-bound build/runtime tests | source lineage, artifact hashes, deployment evidence |
| Observability and operational API | `autonomous-api/app/` and related surfaces | runtime/campaign state → API/events/metrics | unavailable ISR or incomplete lineage must be explicit | endpoint contract, auth, sequence/lineage tests | correlation IDs, event hashes, errors |
| Plugin/backend extension boundary | `compiler/core/protocol.py` + registry | backend implementation → declared identity/capability/test spec | unknown capability defaults to unsupported | plugin conformance, isolation and malicious-plugin tests | signed/versioned backend manifest |

## 3. Concrete boundary crossings and findings

1. **ISR to plan:** `compiler/core/lowering.py` imports ISR node/edge types and behavior validators. This is expected direction for lowering, but the coverage of all ISR semantics must be explicit. The lowerer must not silently discard requirement relationships or semantic kinds it does not map.
2. **Plan to backend:** `compiler/backends/android.py` imports `isr.core.revision.ISRRevision` in addition to the plan and protocol. Its `compile()` consumes a plan, but its public helper `compile_isr_revision()` couples the backend module back to ISR. This is a boundary leak to evaluate and likely move to orchestration/adaptor code after the ADR is approved.
3. **Campaign to compiler and evolution:** `certification/campaign/plan_builder.py` imports the compiler lowerer, evolution constructors, requirement graph and ISR identity. This combines campaign workload construction with multiple pipeline stages. Clarify whether this is a benchmark harness or the canonical production orchestration surface; do not assume it is both.
4. **Campaign runner to application API:** `certification/campaign/runner.py` imports `app.engine.source_bound_full_stack` and verifier surfaces. This makes the execution boundary sensitive to Python path/bootstrap and package coupling; document it and test from a clean environment.
5. **Observation API to ISR:** `autonomous-api/app/main.py` defines `_DbGenerationProvider.get_isr()` as `NotImplementedError`. The API's ISR observation contract is therefore incomplete at this implementation point.
6. **Legacy/reference app versus compiler output:** `autonomous-api/` is a large source subtree, not automatically proof that the compiler can generate or certify it. Maintain explicit generated/reference-source labels and candidate-bound provenance.
7. **Certification authority:** Certification can consume and verify evidence but must not author ISR security obligations. Existing comments in `isr/core/graph.py` explicitly place security policy in ISR and certification as consumer; preserve this boundary.

## 4. Required contract inventory for FS-01/02/03

| Contract | Owner to ratify | Minimum inputs/outputs | Failure behavior | Verification/evidence |
|---|---|---|---|---|
| ISR ↔ Compiler IR (FS-01) | ISR owner + compiler architecture owner | schema IDs/versions, node/edge coverage, canonical forms and hashes | unknown semantic node or unbound relation blocks | mapping completeness, determinism, hashes and coverage report |
| Compiler orchestration (FS-02) | compiler orchestration owner (currently gap) | ISR, backend policy, seed/config → coherent artifact manifest and lineage | failed backend/partial family output quarantined | orchestration integration tests, fault injection, evidence trace |
| Backend/artifact contracts (FS-03) | one owner per backend family, common protocol owner | IR obligations → declared artifacts/tests/evidence | unsupported obligation refuses | native build, behavioral tests, independent verifier |
| Certification/evidence contract | certification governance owner | bound candidate, verifier results → verdict/evidence record | UNKNOWN/corrupt/incomplete chain cannot pass | ledger verification, anti-vacuity and regression tests |
| Deployment/runtime contract | deployment/infrastructure owner | verified artifact and environment → deployment/runtime observations | rollback and unhealthy deployment are non-success | health/lifecycle/rollback tests and deployment evidence |

## 5. Unresolved ownership questions

- Is `CompilationPlan` only a transitional projection, or the first canonical Compiler IR version? Existing contract language indicates stabilization status, so this draft treats canonical IR ownership as unresolved.
- Which module owns full-stack orchestration, distinct from campaign execution and benchmark harnessing?
- Which ledger is authoritative for immutable requirement-to-deployed-artifact lineage across the full compiler path?
- Which deployment surface owns the actual deployed-instance identity and post-deploy observation?
- Which contract is authoritative for unknown ISR primitives and evolution proposals that require new schema semantics?

## 6. Status

**Boundary Integrity: PARTIAL.** Several concrete seams exist, but cross-boundary dependency enumeration is not exhaustive for all modules in the nine roots. Ownership is proposed where source evidence is strong and explicitly marked unresolved where it is not.
