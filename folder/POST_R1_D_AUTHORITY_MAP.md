# POST_R1_D_AUTHORITY_MAP (R1-RG-02)

**Status:** R1-RG-02. One authoritative ownership map. Spec: `folder/postr1d.md` §9.

**Rule applied:** every item has ONE CANONICAL AUTHORITY or CANONICAL + EXPLICIT LEGACY/ADAPTER. No ambiguous ownership acceptable.

---

## 1. Ownership table

| Item | Canonical authority | Legacy/adapter | Evidence |
|---|---|---|---|
| RequirementGraph | `reqgraph/core` | none | RUNTIME_PROVEN (plan_builder; Tier-A) |
| ISR | `isr/core` | LEGACY: `constitutional_architecture/isr/model`, `UniversalISR` (retire R1-D.5) | RUNTIME_PROVEN; R1-D.1 PASS |
| ArchitectureModel | `evolution/core` (Genome) | LEGACY: constitutional `individual.py`, rich `System` (retire R1-D.5) | RUNTIME_PROVEN (constructor in campaign path) |
| ArchitectureCandidate | `evolution/core` (Genome) | same as above | TEST_PROVEN (D04 + R1-D.3) |
| CompilerIR | canonical contract (D07 + D2-D4); stabilization `compiler/core/plan.py` | LEGACY: BIR (donor→retire), per-category `CompilationBundle` (retire) | RUNTIME_PROVEN (stabilization); R1-D.2 PASS |
| Compiler Backend | `compiler/core/protocol.py` | LEGACY: Gen-C ABC, Gen-A base, per-category bases (retire) | RUNTIME_PROVEN (registry + 2 backends) |
| ArtifactSet | canonical boundary (D09; `GeneratedRepository` stabilization) | LEGACY: Gen-A `CompilationOutput` (retire) | RUNTIME_PROVEN (repo on disk; R1-C C06) |
| VerificationResult | canonical verification (D10; 5-state) | LEGACY: Gen-C `verification_pass` fail-open (adapt R1-E.1) | RUNTIME_PROVEN (stages; Tier-A) |
| CertificationEvidence | `certification/evidence` (hash-chained ledger) | none | RUNTIME_PROVEN (B3-v2 ledger intact) |
| RuntimeObservation | D12 contract | LEGACY: `autonomous-api` observation (deferred R2/R3) | DOCUMENTED_ONLY (C-17 deferred) |
| Evaluation | `evolution/core/fitness*.py` + `evolution/governance_fitness_evaluator.py` | LEGACY: constitutional governance fitness (donor; imports removed) | TEST_PROVEN (13 tests) |
| Selection | `evolution/core/selection.py` + `evolution/pareto.py` | LEGACY: constitutional selectors (retire) | TEST_PROVEN |
| EvolutionOperation | `evolution/core/operations.py` | LEGACY: constitutional operators (donor/retire) | TEST_PROVEN (D05 + Part II) |
| EvolutionRecord/EIR | `EvolutionEvent` + `EvolutionHistoryRepository` + `CandidateEvaluationRecord` | LEGACY: constitutional EIR (retire; `transformations=[]` dies with file) | TEST_PROVEN (hash chain, append-only) |
| Lineage | `evolution/core/construction.py` + `history.py` (in-memory) | LEGACY: constitutional trackers (retire); durable R1-E.6 | TEST_PROVEN (D3-07) |
| Provenance | per-contract provenance + certification ledger | none competing | TEST_PROVEN (PlanArtifacts 4-hash correlation) |

---

## 2. Verdict

Zero ambiguous ownership. Every legacy item has an explicit disposition (retire R1-D.5, adapt R1-E.x, or defer R2/R3). No second authority executes in the canonical runtime (verified: no canonical→constitutional runtime imports; R1-D.3 + rg static tests).

---

*End of R1-RG-02.*
