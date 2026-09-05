# CONTRACT_INVARIANTS (R1-B D16)

**Contract:** `Contract Invariant Catalogue`
**Status:** R1-B Deliverable D16. Authoritative formal invariants extending the R1-A invariants. Index: `folder/CANONICAL_CONTRACT_REGISTRY.md` (D01).
**Authority:** R1-A (`folder/CANONICAL_SUBSTRATE_DECISION.md`) and R1-B D02–D12.

---

## 1. Purpose

This catalogue enumerates the formal invariants (INV-B01 through INV-B15) that all canonical contracts must satisfy. The invariants are derived from the R1-A decisions and the R1-B per-contract specifications. Each invariant is binding; a contract that violates any invariant is rejected at construction or registration.

## 2. The 15 invariants

### INV-B01 — One canonical ISR semantic authority

**Statement:** There must be exactly one authoritative semantic representation of an ISR revision. Views, projections, serialized forms, indexes, caches, and backend-specific representations are permitted; none may independently define system semantics.

**Enforced by:** D03 (CanonicalISR), D13 (cross-contract identity).

**Source:** R1-A §0.7 (semantic-authority invariant).

### INV-B02 — RequirementGraph precedes ISR construction

**Statement:** The `RequirementGraph` (D02) is the first canonical contract in the chain. Nothing downstream may produce or modify requirements. ISR construction (D03) consumes the RequirementGraph and references it by content hash.

**Enforced by:** D02 (RequirementGraph), D03 (CanonicalISR).

**Source:** R1-B D02 architecture.

### INV-B03 — ISR is technology-neutral

**Statement:** The `ISR` (D03) must remain technology-neutral, implementation-neutral, backend-neutral, deployment-provider-neutral, and framework-neutral. The 25 forbidden implementation terms in `isr/core/invariants.py:16-42` are the canonical technology-leakage guard.

**Enforced by:** D03 (CanonicalISR), the forbidden-term validator.

**Source:** R0 audit; R1-B D03.

### INV-B04 — Architecture Model is distinct from ISR

**Statement:** The `ArchitectureCandidate` (D04) is distinct from the `ISR` (D03). An ArchitectureCandidate references an ISR revision by content hash but does not duplicate its semantics. An ArchitectureCandidate that defines system semantics independently of its referenced ISR is rejected.

**Enforced by:** D04 (ArchitectureCandidate), the `ArchitectureCandidateSemanticDuplication` failure condition.

**Source:** R1-A architectural principle; R1-B D04.

### INV-B05 — Compiler IR is distinct from ISR

**Statement:** The `CompilerIR` (D07) is distinct from the `ISR` (D03). The CompilerIR references the ISR by content hash but does not duplicate its semantics. The CompilerIR contains compilation-level concepts (component model, interfaces, data flows, persistence, API contracts, etc.) that are not in the ISR.

**Enforced by:** D07 (CanonicalCompilerIR), the `BrokenLineage` and `HashMismatch` failure conditions.

**Source:** R1-A architectural principle; R1-B D07.

### INV-B06 — Compiler IR is distinct from generated artifacts

**Statement:** The `CompilerIR` (D07) is distinct from the `ArtifactSet` (D09). The CompilerIR is a planning structure; the ArtifactSet is the generated-software boundary. The two are linked by the compilation identity (D08 CompilerBackend consumes the IR and produces the ArtifactSet).

**Enforced by:** D07, D08, D09. The D09 traceability invariant (Requirement → ... → ArtifactSet) is enforced at construction.

**Source:** R1-A architectural principle; R1-B D07, D09.

### INV-B07 — Evolution does not depend on backend technology

**Statement:** The Evolution engine (`evolution/`) must not depend on backend technology. The EvolutionOperation (D05) and EvolutionRecord (D06) operate on `ArchitectureCandidate` (D04), which references an ISR revision. They do not reference a `CompilerBackend` (D08) or a technology-specific capability.

**Enforced by:** D05 (EvolutionOperation), D06 (EvolutionRecord), D04 (ArchitectureCandidate). The deprecation of `constitutional_architecture/engine/mutation_*.py` (R1-D.5) and the retirement of `constitutional_architecture/engine/crossover_engine.py` ensure that the Substrate B path (which is technology-aware) does not become a second evolution runtime.

**Source:** R0 audit; R1-B D04, D05, D06.

### INV-B08 — Backend cannot redefine upstream semantics

**Statement:** A `CompilerBackend` (D08) must not redefine ISR semantics, modify the RequirementGraph, own architecture evolution, become a verification authority, directly mutate certification state, or silently write arbitrary files outside `ArtifactSet` semantics. A backend that performs any of these is rejected at registration.

**Enforced by:** D08 (CompilerBackend) registration check; the canonical protocol at `compiler/core/protocol.py`.

**Source:** R1-B D08.

### INV-B09 — ArtifactSet is the generated-software boundary

**Statement:** Every generated artifact is in an `ArtifactSet` (D09). The ArtifactSet is the boundary between the canonical compiler and the technology-specific implementation. Backends emit `ArtifactSet`; the packager writes. There is no implicit API for backend filesystem emission.

**Enforced by:** D09 (ArtifactSet), the `ARTIFACT_SET_INCOMPLETE` and `BROKEN_LINEAGE` failure conditions. The `self.write_files()` defect in `constitutional_architecture/compiler/backends/fastapi_backend.py:72-86` is corrected in R1-E.7 or the backend is retired.

**Source:** R1-B D09.

### INV-B10 — Verification cannot fail open

**Statement:** A verifier that catches an internal exception and returns `PASS` is rejected at registration. The correct outcome is `INDETERMINATE` with `indeterminate_reason` populated. The 5-state model (`PASS`, `FAIL`, `INDETERMINATE`, `NOT_RUN`, `BLOCKED`) is mandatory for D10.

**Enforced by:** D10 (VerificationResult) registration check; the mandatory state model. The fail-open defect in `constitutional_architecture/compiler/passes/verification_pass.py:12-132` is adapted or the path is retired (R1-E.1).

**Source:** R0 audit; R1-B D10.

### INV-B11 — Certification cannot manufacture verification evidence

**Statement:** A `CertificationEvidence` (D11) record cannot be created without a corresponding `VerificationResult` (D10). A certification status that contradicts the verification result (e.g. `CERTIFIED` with `VerificationResult.FAIL` or `VerificationResult.INDETERMINATE`) is rejected at construction. The certifier's local opinion is not a substitute for evidence.

**Enforced by:** D11 (CertificationEvidence) construction check; the derivation of certification state from verification state (D14).

**Source:** R1-B D11; D14 cross-contract state mapping.

### INV-B12 — Runtime observations retain reverse lineage

**Statement:** A `RuntimeObservation` (D12) must include the full reverse lineage: deployment → ArtifactSet → CompilerIR → Architecture → ISR → RequirementGraph. An observation with missing reverse lineage cannot be attached to the evidence chain and is rejected at construction.

**Enforced by:** D12 (RuntimeObservation) construction check.

**Source:** R1-B D12.

**Note:** The implementation of this invariant is out of R1 scope (C-17 deferred to R2/R3). The contract surface is defined in D12; the runtime instrumentation is deferred.

### INV-B13 — Historical evidence is immutable

**Statement:** The B3-v2 evidence chain is preserved unchanged. R1-B does not alter historical certification evidence. New campaign identities (R2, the post-migration certification baseline) produce new evidence chains. The old chain is preserved as historical evidence.

**Enforced by:** D11 (CertificationEvidence) immutability rule. The hash chain is append-only; no record is modified or deleted.

**Source:** R1-A evidence-preservation rationale; R1-B D11.

### INV-B14 — No category-specific compiler becomes a new architectural authority

**Statement:** The 9 per-category compilers in `constitutional_architecture/compilers/` (backend, database, deployment, documentation, frontend, infrastructure, operational, runtime_policy, testing) are retired as runtime. They do not become a second set of architectural authorities.

**Enforced by:** R1-D.5 (deprecation of per-category compilers). The canonical backend protocol (D08) is the only backend protocol.

**Source:** R1-A canonical module map; R1-B D08.

### INV-B15 — Legacy adapters are one-way

**Statement:** Adapters are always `LEGACY → CANONICAL`, never `CANONICAL ↔ LEGACY`. A bidirectional adapter recreates the dual-source-of-truth problem (audit §39 NO NEW SOURCE OF TRUTH) and is forbidden.

**Enforced by:** D17 (legacy boundary specification); the adapter direction field in the legacy boundary table.

**Source:** R1-A migration principles; R1-B D17.

## 3. Invariant verification

Each invariant is verified by:

1. **Construction check:** a contract that violates the invariant is rejected at construction.
2. **Registration check:** a backend that violates INV-B08 is rejected at registration.
3. **State machine enforcement:** a state transition that violates the failure-semantics discipline is rejected (D14).
4. **Contract test:** each invariant has a corresponding contract test (D18).

## 4. Extension mechanism

- New invariants require an ADR.
- New failure conditions for an existing invariant require an ADR.
- The invariant catalogue is frozen; extensions are versioned.

## 5. Cross-references

- D02–D12: per-contract enforcement.
- D13: cross-contract identity (enforces lineage invariants).
- D14: state machine and failure semantics (enforces INV-B10, INV-B11).
- D17: legacy boundary (enforces INV-B15).
- D18: contract test specification (each invariant has a test).
- D20: R1-B gate report (the gate evaluates whether the invariants are consistent with the per-contract specs).

---

*End of D16. The 15 contract invariants (INV-B01 through INV-B15) are the binding rules that all canonical contracts must satisfy. The invariants are derived from the R1-A decisions and the R1-B per-contract specifications.*
