# R1_B_CONTRACT_GATE_REPORT (R1-B D20)

**Status:** R1-B Deliverable D20. The R1-B gate report. Evaluates whether D01–D19 collectively establish enough architectural certainty for R1-C. Final verdict below.

**Authority:** R1-A canonical substrate decision; R1-B D01–D19.

**Method:** Independent evaluation of each of the 12 gate questions against the deliverables. Cross-checks for contradictions between D02–D12 (per-contract specifications) and D13–D19 (cross-contract constitution). Identifies any blocking conditions.

---

## 1. Executive verdict

**R1-B: PASS.**

D01–D19 collectively establish enough architectural certainty for R1-C (adapters + migration). The 12 gate questions are answered below. No contradictions were discovered between the per-contract specifications (D02–D12) and the cross-contract model (D13–D19). The canonical substrate is sufficiently constrained for R1-C to begin.

**Two cross-contract decisions** were made in D14 (state machine & failure semantics) that resolve gaps the per-contract specifications left open. Both are recorded in §3 below. They are not contradictions; they are necessary decisions the cross-contract model made to ensure consistency.

**R1-B does not authorize R1-C implementation.** R1-C is the next gate; it requires separate explicit authorization per the user's governance discipline. R1-B PASS is the gate that allows R1-C to begin; the user's authorization to begin R1-C is the next step.

## 2. The 12 gate questions

### Q1. Are all canonical contracts defined?

**Answer: YES.**

The 11 canonical contracts are defined across D02–D12:

| # | Contract | Specification |
|---|---|---|
| 1 | `RequirementGraph` | `folder/CONTRACT_RequirementGraph.md` (D02) |
| 2 | `ISR` | `folder/CONTRACT_CanonicalISR.md` (D03) |
| 3 | `ArchitectureCandidate` | `folder/CONTRACT_ArchitectureCandidate.md` (D04) |
| 4 | `EvolutionOperation` | `folder/CONTRACT_EvolutionOperation.md` (D05) |
| 5 | `EvolutionRecord / EIR` | `folder/CONTRACT_EvolutionRecord_EIR.md` (D06) |
| 6 | `CompilerIR` | `folder/CONTRACT_CanonicalCompilerIR.md` (D07) |
| 7 | `CompilerBackend` | `folder/CONTRACT_CompilerBackend.md` (D08) |
| 8 | `ArtifactSet` | `folder/CONTRACT_ArtifactSet.md` (D09) |
| 9 | `VerificationResult` | `folder/CONTRACT_VerificationResult.md` (D10) |
| 10 | `CertificationEvidence` | `folder/CONTRACT_CertificationEvidence.md` (D11) |
| 11 | `RuntimeObservation` | `folder/CONTRACT_RuntimeObservation.md` (D12) |

The registry (D01) is the index. All 11 contracts are present, indexed, and cross-referenced.

### Q2. Is ownership unambiguous?

**Answer: YES.**

Each contract in D02–D12 has a **canonical owner** at the module level. The ownership is unambiguous:

- D02: `reqgraph/core`
- D03: `isr/core`
- D04–D06: `evolution/core`
- D07 (CompilerIR): canonical module to be created in R1-D.2; stabilization owner is `compiler/core`
- D08: `compiler/core/protocol.py`
- D09 (ArtifactSet): canonical module to be created in R1-D.5; stabilization owner is `compiler/core/repository.py`
- D10 (VerificationResult): canonical interface to be created; stabilization owner is `certification/stages/`
- D11: `certification/evidence/`
- D12 (RuntimeObservation): contract defined in R1-B; implementation deferred (C-17)

Legacy components in D17 have explicit owners for retirement.

### Q3. Is ISR authority unambiguous?

**Answer: YES.**

The canonical ISR is `isr/core/`. The semantic-authority invariant (INV-B01, D16) is explicit: there is exactly one authoritative semantic representation of an ISR revision; views, projections, indexes, caches, and backend-specific representations are permitted; none may independently define system semantics.

The legacy ISRs (L01 `constitutional_architecture/isr/model/isr.py:ISR`, L02 `constitutional_architecture/core/models/isr.py:UniversalISR`) are explicitly classified in D17 as LEGACY and are retired as runtime per R1-D.5. L01's semantic validators are selectively migrated to `isr/core/invariants.py` in R1-D.1.

The rich `System/Module/Entity/...` model in L01 is **not** the canonical ISR. The canonical ISR is flat (9 NodeType, 8 EdgeType, frozen Pydantic, SHA-256 content hash, 25 forbidden terms).

### Q4. Is Compiler IR distinct from ISR?

**Answer: YES.**

D07 (CompilerIR) explicitly establishes:

```text
Canonical ISR
      ↓
Architecture Model
      ↓
Compiler IR
      ↓
Backend Lowering
      ↓
ArtifactSet
```

The CompilerIR is a distinct semantic surface. The contract references the ISR by content hash (D07 §6) but does not duplicate ISR semantics. INV-B05 (D16) enforces this distinction.

The R1-A C-03 refinement is concretely implemented in D07: `CompilationPlan` is the stabilization implementation, not the final architectural definition; the canonical CompilerIR is a new module (R1-D.2). BIR is a semantic donor, not the implementation. Content-hash is added to the canonical CompilerIR, not to BIR.

### Q5. Is Compiler IR distinct from Architecture Model?

**Answer: YES.**

D04 (ArchitectureCandidate) and D07 (CompilerIR) are separate contracts. The ArchitectureCandidate references an ISR revision by content hash; it does not define system semantics independently of the ISR. The CompilerIR references the ArchitectureCandidate and the ISR by content hash; it contains compilation-level concepts (component model, interfaces, data flows, persistence, API contracts, etc.) that are not in the ArchitectureCandidate.

INV-B04 (Architecture Model is distinct from ISR) and INV-B05 (Compiler IR is distinct from ISR) are enforced.

### Q6. Is ArtifactSet the compiler output boundary?

**Answer: YES.**

D09 (ArtifactSet) explicitly establishes ArtifactSet as the generated-software boundary. The contract distinguishes four artifact kinds (`generated artifact` / `compiler workspace` / `temporary build output` / `runtime deployment artifact`) and enforces that backend emission is via `ArtifactSet`, not direct filesystem writes.

The `self.write_files()` defect in `constitutional_architecture/compiler/backends/fastapi_backend.py:72-86` is explicitly classified in D17 (L11) as a defect to be corrected in R1-E.7 (or the backend is retired). INV-B09 enforces the boundary.

### Q7. Are verification failures fail-closed?

**Answer: YES.**

D10 (VerificationResult) mandates the 5-state model: `PASS`, `FAIL`, `INDETERMINATE`, `NOT_RUN`, `BLOCKED`. The mandatory invariant is explicit: an internal verifier exception produces `INDETERMINATE`, not `PASS`.

D14 (state machine) establishes the universal failure-semantics discipline: Validation failure ≠ warning; Verification exception ≠ success; Unsupported backend capability ≠ successful compilation; Missing evidence ≠ certified.

The fail-open defect in `constitutional_architecture/compiler/passes/verification_pass.py:12-132` is explicitly classified in D17 (L12) as a defect to be adapted in R1-E.1 (or the path is retired). INV-B10 (Verification cannot fail open) is enforced.

### Q8. Is certification downstream of evidence?

**Answer: YES.**

D11 (CertificationEvidence) requires that a CertificationEvidence record cannot be created without a corresponding VerificationResult. The certification state is derived from the verification state per D14 §5: `PASS` → `CERTIFIED`; `FAIL` → `NOT_CERTIFIED`; `INDETERMINATE` → `INDETERMINATE`; `NOT_RUN` → `BLOCKED`; `BLOCKED` → `BLOCKED`.

The certifier cannot manufacture evidence (INV-B11). A certification status that contradicts the verification result is rejected at construction. The B3-v2 evidence chain is preserved unchanged (INV-B13).

### Q9. Is runtime lineage defined?

**Answer: YES (with C-17 deferral noted).**

D12 (RuntimeObservation) defines the reverse lineage: deployment → ArtifactSet → CompilerIR → Architecture → ISR → RequirementGraph. The contract enforces the lineage at construction; an observation with missing reverse lineage is rejected.

**Caveat:** The contract is defined in R1-B; the implementation is out of R1 scope. C-17 (`autonomous-api/` observation lineage) is deferred to R2/R3 platform integration. The contract surface is sufficient for the runtime lineage requirement; the runtime instrumentation is deferred.

### Q10. Are legacy boundaries explicit?

**Answer: YES.**

D17 (legacy boundary specification) enumerates 14 legacy components (L01–L14) with explicit classifications:

- `LEGACY` classification at the module level
- `Owner` (the migration step that retires the component)
- `Purpose` (what the component does)
- `Input` and `Output` (its interface)
- `Canonical destination` (the canonical contract it will be replaced by)
- `Adapter direction` (`LEGACY → CANONICAL`, never `CANONICAL ↔ LEGACY`)
- `Retirement condition` (the criterion for retiring the component)

INV-B15 (legacy adapters are one-way) is enforced. A legacy component without these markings is forbidden.

### Q11. Are BIR/EIR/Gen-C semantic contributions classified?

**Answer: YES.**

D15 (compatibility matrix) classifies each B component with an action (KEEP, MIGRATE, ADAPT TEMPORARILY, RETIRE, DEFER) and rationale. Specifically:

- **BIR (L07):** semantic donor; the 9 BIRNodeTypes are read as references and selectively absorbed into the canonical CompilerIR contract where genuinely semantic. **Not modified to add content-hash.** Retired as runtime per R1-D.5.
- **Constitutional EIR (L06):** useful schema fragments selectively absorbed into the canonical `EvolutionRecord` (R1-D.3). The `transformations=[]` defect is repaired or the path is retired.
- **Gen-C (compiler/passes/, backends/):** fail-open verification pass (L12) and `self.write_files()` defect (L11) are adapted in R1-E.1 and R1-E.7 respectively, or the paths are retired. Gen-C ABC (L08) is retired.
- **Gen-A (compiler/sdk/base.py, CompilationOutput):** retired as runtime (L09, plus L08 in D15).
- **Per-category compilers (L10):** retired; INV-B14 (no category-specific compiler becomes a new architectural authority) is enforced.

The migration actions are scheduled per R1-D and R1-E; the D19 migration constraints are the binding rules.

### Q12. Can R1-C begin without architectural ambiguity?

**Answer: YES.**

D13 (cross-contract identity & provenance) + D14 (state machine) + D15 (compatibility matrix) + D16 (invariants) + D17 (legacy boundary) + D19 (migration constraints) collectively establish enough architectural certainty for R1-C to begin. Specifically:

- Every contract has a content-hash identity (D13).
- Every cross-contract reference is by content hash (D13).
- The state machine is consistent across contracts (D14).
- The compatibility matrix specifies what to KEEP, MIGRATE, ADAPT, RETIRE, DEFER (D15).
- The 15 INV-B invariants are binding (D16).
- The legacy boundary classifies every surviving legacy component (D17).
- The migration constraints specify what R1-C and R1-D may and may not change (D19).

The contract tests (D18) are the architectural acceptance tier for R1-C. Each R1-C step is gated by the contract tests passing, the 243 Tier A CBC1 tests still passing, and explicit user authorization (D19 §5).

## 3. Cross-contract decisions accepted by the gate

Two cross-contract decisions were made in D14 (state machine & failure semantics) that resolve gaps the per-contract specifications left open. Both are recorded here as decisions the gate has accepted.

### Decision A: Backend `UNSUPPORTED_CAPABILITY` → Verification `INDETERMINATE`

D08 (CompilerBackend) defines `UNSUPPORTED_CAPABILITY` as an explicit outcome. D10 (VerificationResult) defines the 5-state model (`PASS`/`FAIL`/`INDETERMINATE`/`NOT_RUN`/`BLOCKED`). D14 §4 maps backend-level `UNSUPPORTED_CAPABILITY` to verification-level `INDETERMINATE`: a backend that cannot lower a capability produces no `ArtifactSet`, so the verifier cannot run; the result is `INDETERMINATE` (not `PASS`, not `FAIL`).

This is the explicit answer to the audit's "unsupported backend capability ≠ successful compilation" requirement (R0 audit; D14 §6 universal discipline).

### Decision B: Certification `INDETERMINATE` (not `CERTIFIED`) when verification is `INDETERMINATE`

D11 (CertificationEvidence) derives certification state from verification state. D14 §5 specifies: `VerificationResult.INDETERMINATE` → `CertificationEvidence.INDETERMINATE`, not `CERTIFIED`. The certifier cannot manufacture evidence (INV-B11).

This is the explicit answer to the audit's "certification cannot manufacture verification evidence" requirement (R0 audit; D14 §6 universal discipline).

## 4. Contradictions discovered

**None.**

The cross-checks between D02–D12 (per-contract specifications) and D13–D19 (cross-contract constitution) found no contradictions. The 12 gate questions are answered without blocking conditions.

## 5. R1-B deliverable summary

| # | Deliverable | File |
|---|---|---|
| D01 | Canonical Contract Registry | `folder/CANONICAL_CONTRACT_REGISTRY.md` |
| D02 | RequirementGraph contract | `folder/CONTRACT_RequirementGraph.md` |
| D03 | CanonicalISR contract | `folder/CONTRACT_CanonicalISR.md` |
| D04 | ArchitectureCandidate contract | `folder/CONTRACT_ArchitectureCandidate.md` |
| D05 | EvolutionOperation contract | `folder/CONTRACT_EvolutionOperation.md` |
| D06 | EvolutionRecord / EIR contract | `folder/CONTRACT_EvolutionRecord_EIR.md` |
| D07 | CanonicalCompilerIR contract | `folder/CONTRACT_CanonicalCompilerIR.md` |
| D08 | CompilerBackend contract | `folder/CONTRACT_CompilerBackend.md` |
| D09 | ArtifactSet contract | `folder/CONTRACT_ArtifactSet.md` |
| D10 | VerificationResult contract | `folder/CONTRACT_VerificationResult.md` |
| D11 | CertificationEvidence contract | `folder/CONTRACT_CertificationEvidence.md` |
| D12 | RuntimeObservation contract | `folder/CONTRACT_RuntimeObservation.md` |
| D13 | Cross-contract identity & provenance | `folder/CONTRACT_CrossContractIdentity_Provenance.md` |
| D14 | State machine & failure semantics | `folder/CONTRACT_State_FailureSemantics.md` |
| D15 | Compatibility matrix | `folder/R1_B_COMPATIBILITY_MATRIX.md` |
| D16 | Contract invariants (INV-B01…INV-B15) | `folder/CONTRACT_INVARIANTS.md` |
| D17 | Legacy boundary specification | `folder/CONTRACT_LegacyBoundarySpecification.md` |
| D18 | Contract test specification | `folder/CONTRACT_TestSpecification.md` |
| D19 | Migration constraints | `folder/R1_B_MIGRATION_CONSTRAINTS.md` |
| D20 | R1-B gate report (this document) | `folder/R1_B_CONTRACT_GATE_REPORT.md` |

## 6. Conditions for R1-C

R1-B PASS is the gate that allows R1-C to begin. R1-C requires **separate explicit authorization** from the user, per the governance discipline established in R1-A.

When R1-C begins, the following conditions hold:

1. The canonical runtime code (`isr/core/`, `compiler/`, `evolution/`, `reqgraph/`, `certification/`, `release/evidence/`) is **unfrozen** for the migration window.
2. R1-C may introduce temporary `LEGACY → CANONICAL` adapters (per D17, INV-B15).
3. Each R1-C step is gated by:
   - The contract tests for the affected contracts (D18) pass.
   - The 243 Tier A CBC1 tests still pass.
   - The migration step is explicitly authorized by the user.
4. The B3-v2 evidence chain is preserved unchanged (INV-B13).
5. No second source of truth, no bidirectional adapters, no introduction of a parallel runtime (D19).
6. R1-C is bounded: it ends when all legacy components in D17 are either retired or have explicit retirement conditions that are not yet met (with a recorded plan).

## 7. Conditions for R1-D, R1-E, R1-F

Each subsequent R1 phase requires separate explicit authorization. The sequencing per the R1 plan is:

- **R1-C** — Adapters + migration (begin after R1-B PASS).
- **R1-D** — Semantic migration (begin after R1-C complete; migration actions per D15).
- **R1-E** — Correctness repairs (canonical contracts first, then Gen-C adaptations; per the user's correction 2).
- **R1-F** — Post-migration certification baseline (new campaign identity, NOT a re-certification of B3-v2).

## 8. Final verdict

**R1-B: PASS.**

The canonical contracts are defined. The cross-contract constitution is consistent. The migration constraints are binding. The legacy boundary is explicit. The invariants are enforced. The state machine is consistent.

R1-C is the next gate. It does not begin until the user explicitly authorizes it.

---

*End of D20. R1-B is complete. The R1-B gate report is the authoritative record of the gate evaluation. The canonical substrate is sufficiently constrained for the next phase.*
