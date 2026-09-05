# POST_R1_D_DATAFLOW_RECONCILIATION (R1-RG-04)

**Status:** R1-RG-04. Forward and reverse data flow. Spec: `folder/postr1d.md` §§15–16.

**Classification per edge:** RUNTIME / TEST / STATIC / CONTRACT / UNKNOWN. No invented evidence.

---

## 1. Forward lineage (Requirement → RuntimeObservation)

| Edge | Classification | Evidence |
|---|---|---|
| Requirement → RequirementGraph node | TEST | genesis mapper + requirement-graph tests; manual extractor (autonomous extraction deferred) |
| RequirementGraph node → ISR node | RUNTIME | `plan_builder.py` builds rg then rev0 with `requirement_refs=sorted(rg.nodes)` |
| ISR node → ArchitectureCandidate | RUNTIME | `ReferenceGenomeConstructor.construct(rev0)` in campaign path |
| ArchitectureCandidate → CompilerIR | RUNTIME (mediated) | Genome → `ReferenceGenomeMaterializer` → rev1 → `isr_to_plan`; see RG-01 note 1 |
| CompilerIR → ArtifactSet | RUNTIME | `backend.compile(plan)` (`runner.py:90`); two backends |
| ArtifactSet → Verification | RUNTIME | stages + `backend.conformance(plan, repo)` (`runner.py:109`); independent re-derivation |
| Verification → RuntimeObservation | CONTRACT | D12 defines the edge; runtime implementation deferred (C-17) |

## 2. Reverse lineage (RuntimeObservation → Parent)

| Edge | Classification | Evidence |
|---|---|---|
| RuntimeObservation → ArtifactSet | CONTRACT | D12 reverse-lineage fields (`artifact_set_id`, `compiler_ir_id`, `architecture_candidate_id`, `isr_revision_hash`, `requirement_graph_id`); rg test pins fields |
| ArtifactSet → CompilerIR | RUNTIME | `plan.isr_id` + `plan_hash` in `PlanArtifacts`; independent_verify re-derives from repo + plan hash |
| CompilerIR → ArchitectureCandidate | CONTRACT | D2-D4 `source_architecture_content_hash` (R1-D.5); today via rev1 `parent_revision_id` + genome hash in `PlanArtifacts` |
| ArchitectureCandidate → EvolutionRecord | TEST | OperationRecord sources + history hash chain (R1-D.3 tests) |
| EvolutionRecord → EvolutionOperation | TEST | record carries `operation_type`, parameters, seed |
| EvolutionOperation → Parent Candidate | TEST | source ids preserved; multi-generation chain test |

## 3. Evolution lineage (in-loop)

Linear, branching, and crossover graphs: TEST (6 R1-D.3 lineage tests). Hash-chained history: TEST (append-only + link tests). Durable store: CONTRACT (R1-E.6).

## 4. Verdict

Forward path RUNTIME end-to-end except the final RuntimeObservation edge (CONTRACT). Reverse path RUNTIME except RuntimeObservation↔ArtifactSet and ArchitectureCandidate↔CompilerIR direct-consumption links (CONTRACT, with runtime-sufficient mediated equivalents). Objective (§16) is met: contracts permit and preserve reverse lineage; no new provenance authority needed.

---

*End of R1-RG-04.*
