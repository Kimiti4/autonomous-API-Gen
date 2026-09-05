# POST_R1_D_RECONCILIATION_MATRIX (R1-RG-01)

**Status:** Reconciliation deliverable R1-RG-01. Cross-layer matrix. Spec: `folder/postr1d.md` §8.

**Authority:** R1-A; R1-B D02–D20; R1-C C01–C12; R1-D.1–D.3 gates; `folder/postr1d.md`.

**Evidence classes (§6):** RUNTIME_PROVEN / TEST_PROVEN / STATIC_ONLY / DOCUMENTED_ONLY / UNKNOWN. Runtime edges below cite file:line + test.

---

## 1. Matrix

| Layer | Canonical Authority | Input | Output | Consumer | Evidence | Status |
|---|---|---|---|---|---|---|
| Requirements | external (human/environment) | stakeholder need | RequirementGraph | ISR construction | TEST_PROVEN (`tests/test_cap_a_requirement_graph.py`, genesis mapper) | IMPLEMENTED (manual extractor; autonomous extraction deferred) |
| RequirementGraph | `reqgraph/core` | requirements | typed graph | ISR construction | RUNTIME_PROVEN (`certification/campaign/plan_builder.py` builds rg; `PlanArtifacts.requirement_graph_hash`) | IMPLEMENTED |
| ISR | `isr/core` | RequirementGraph | `ISRRevision` (content-hash) | Architecture construction | RUNTIME_PROVEN (`plan_builder.py:125-142`; `ISRRevision.create` fail-closed; 243 Tier-A) | IMPLEMENTED |
| Architecture | `evolution/core` (Genome) | ISRRevision | `Genome` (content-hash) | Compiler lowering (via materialization) | RUNTIME_PROVEN (`ReferenceGenomeConstructor.construct`, `plan_builder.py:130-141`) | IMPLEMENTED |
| CompilerIR | canonical contract (D07 + D2-D4); stabilization `compiler/core/plan.py` | Architecture (via materialized ISR) | `CompilationPlan` | Backend | RUNTIME_PROVEN (`isr_to_plan` at `plan_builder.py:142`; `runner.py:90`) | IMPLEMENTED (stabilization; canonical module R1-D.5) |
| Backend | `compiler/core/protocol.py` | CompilerIR | `GeneratedRepository` | Verification | RUNTIME_PROVEN (`runner.py:90,109`; two canonical backends) | IMPLEMENTED |
| ArtifactSet | canonical boundary (D09; `GeneratedRepository` stabilization) | compiler output | software repo | Verification/Runtime | RUNTIME_PROVEN (repo on disk; `independent_verify.py:18-35` re-derives conformance) | IMPLEMENTED (stabilization) |
| Verification | canonical verification (D10; 5-state) | ArtifactSet | evidence/result | Certification/Evolution | RUNTIME_PROVEN (stages; `compose_verdict` at `runner.py:159`) | IMPLEMENTED (structural; behavioral via docker gates) |
| Runtime | canonical observation (D12 contract) | deployed artifact | observations | Evaluation | DOCUMENTED_ONLY (contract; C-17 deferred) | CONTRACTUALLY READY |
| Evaluation | canonical evaluation surface | evidence | score/result | Selection | TEST_PROVEN (fitness + governance evaluator; 12 + 1 tests) | IMPLEMENTED (canonical evidence; runtime-evidence consumer deferred) |
| Selection | canonical selection surface | candidates/evaluation | selected candidate | Evolution | TEST_PROVEN (`select_pareto`; Pareto tests) | IMPLEMENTED |
| Evolution | `evolution/` + `evolution/core` | ArchitectureCandidate | new candidate | Compiler | TEST_PROVEN (mutation/crossover/selection/lineage; 32 R1-D.3 tests) | IMPLEMENTED |
| Lineage | canonical lineage (D3-07) | transitions | ancestry | Provenance | TEST_PROVEN (OperationRecord + hash-chained history) | IMPLEMENTED (in-memory; durable R1-E.6) |

---

## 2. Edge notes (honest classifications)

1. **Architecture → CompilerIR is RUNTIME via ISR materialization** (`Genome` → `ReferenceGenomeMaterializer` → `ISRRevision rev1` → `isr_to_plan`). The compiler consumes the materialized ISR, not the Genome object directly. Lineage is preserved (`rev1` carries `parent_revision_id=rev0`, `created_by=evolution_engine`, genome hash in `PlanArtifacts`). No bypass: the materializer is ADR-011 §Genome→ISR bridge, tested. Classification: RUNTIME (mediated) — documented here, not a blocker.
2. **CompilerIR identity is derived, canonical hash is contract.** `plan_id` derives from the ISR hash; `plan_hash` covers the serialized plan; canonical content-hash is D2-D4 contract with implementation in R1-D.5. Correlation is sufficient today via `PlanArtifacts`. Classification: RUNTIME (derived) + CONTRACTUALLY READY (canonical). Not a blocker.
3. **Runtime → Evaluation is CONTRACTUALLY READY.** D12 + D14 mapping exist; runtime implementation deferred (C-17). Per §23 this must not be called implemented. Classification: CONTRACTUALLY READY. Not a blocker (authorized deferral, no contradiction).
4. **Verification vocabulary layers consistently:** 5-state verification (D10) → binary trial (`CERTIFIED`/`NOT_CERTIFIED`, fail-closed default `trial.py:75`) → 3-state campaign (`CERTIFIED`/`QUALIFIED_PARTIAL`/`NOT_CERTIFIED`, honesty rule `verdict.py:1-3`). Each layer preserves the fail-closed direction. No contradiction.

---

*End of R1-RG-01.*
