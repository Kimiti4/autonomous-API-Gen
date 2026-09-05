# POST_R1_D_SEMANTIC_RECONCILIATION (R1-RG-03)

**Status:** R1-RG-03. Cross-contract semantic relationships and contradictions. Spec: `folder/postr1d.md` §10.

**Method:** pairwise compatibility check across the 11 contracts for identity rules, field names, lifecycle states, failure semantics, version semantics, provenance, hashing, parent/child semantics, timestamps, determinism. Differences classified as semantic contradictions vs representation differences.

---

## 1. Pairwise results

| Pair | Check | Result |
|---|---|---|
| RequirementGraph ↔ ISR | `REQUIREMENT_REF.ref_id` ↔ graph node ids | COMPATIBLE (RUNTIME_PROVEN: `PlanArtifacts` carries both + hashes) |
| ISR ↔ ArchitectureCandidate | Genome built from `ISRRevision`; `parent_revision_id` chain | COMPATIBLE (RUNTIME_PROVEN: rev0 → Genome → rev1 in plan_builder) |
| ArchitectureCandidate ↔ CompilerIR | IR references architecture (contract) vs IR built from materialized ISR (runtime) | COMPATIBLE with noted mediation (RG-01 note 1); `source_architecture_content_hash` is D2-D4 contract (R1-D.5) |
| CompilerIR ↔ Backend | `CompilationPlan` → `CompilerBackend.compile` | COMPATIBLE (RUNTIME_PROVEN: `runner.py:90`) |
| Backend ↔ ArtifactSet | repo emission, no filesystem write in `compile()` | COMPATIBLE (R1-C C06; 15 tests) |
| ArtifactSet ↔ Verification | repo on disk + plan hash → conformance | COMPATIBLE (RUNTIME_PROVEN: `independent_verify.py`) |
| Verification ↔ CertificationEvidence | 5-state → binary trial → 3-state campaign | COMPATIBLE (layered, fail-closed direction preserved; RG-01 note 4) |
| Verification ↔ Evolution | `UNSUPPORTED_CAPABILITY` → `INDETERMINATE` → not certified; governance zeros → Pareto exclusion | COMPATIBLE (D14; tested) |
| EvolutionOperation ↔ EvolutionRecord | operation executes → record accounts (distinct concepts) | COMPATIBLE (D05/D06 separation preserved) |
| ISR identity ↔ CompilerIR identity | SHA-256 revision hash → derived `plan_id` + `plan_hash` | COMPATIBLE (sufficient correlation; canonical hash R1-D.5) |
| Timestamps | ISO8601 `created_at` (ISR provenance) vs event timestamps (history) vs `evaluated_at` (fitness) | REPRESENTATION DIFFERENCE (each contract-scoped; no shared clock assumption) |
| Version semantics | ISR `schema_version` semver vs genome identity-as-version vs IR `schema_version` contract (R1-D.5) | REPRESENTATION DIFFERENCE (no cross-contract version comparison exists) |
| Determinism | seeded RNG (evolution) vs deterministic lowering vs content hashes | COMPATIBLE (reproducibility tested per layer) |
| Parent/child | single-parent (mutation) + dual-parent (crossover) in both OperationRecord and history | COMPATIBLE |

---

## 2. Contradictions found

**None.** Zero semantic contradictions. Two representation differences (timestamps, version strings) are contract-scoped and never compared across contracts. Both classified R1 (documentation-level; recorded here).

---

## 3. Findings

| ID | Class | Description |
|---|---|---|
| RG-S01 | R1 | Timestamps are per-contract ISO8601 strings with no shared clock; cross-contract temporal ordering relies on causal chain (parent refs + ledger order), not clock comparison. Documented. |
| RG-S02 | R1 | Version strings are per-contract (`schema_version` vs identity-as-version); no cross-contract version negotiation exists. Documented. |

No R2–R5 findings in semantic reconciliation.

---

*End of R1-RG-03.*
