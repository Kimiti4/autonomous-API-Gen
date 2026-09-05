# R1_B_MIGRATION_CONSTRAINTS (R1-B D19)

**Status:** R1-B Deliverable D19. Authoritative specification of what R1-C (adapters + migration) and R1-D (semantic migration) **may** and **may not** change. The constraints are derived from the canonical contracts (D02–D12), the invariants (D16), the legacy boundary (D17), and the R1-A canonical-substrate decision.

**Authority:** R1-A canonical substrate decision; R1-B D02–D18.

---

## 1. Purpose

The migration constraints are the binding rules for R1-C and R1-D. They prevent architectural drift during the migration: the migration must consolidate onto the canonical substrate, not introduce new sources of truth, not weaken verification, not manufacture certification, and not rewrite historical evidence.

## 2. MAY — Permitted changes in R1-C / R1-D

### 2.1 May add canonical contract definitions

- New canonical contracts are added to the registry (D01).
- New contract surfaces require an ADR.
- The contract surface is frozen; extensions are versioned.

### 2.2 May add semantic validators

- Semantic validators from `constitutional_architecture/isr/semantics/*` are selectively migrated into `isr/core/invariants.py` (or a new `isr/core/semantics/`) in R1-D.1.
- The validators must be fail-closed and must not weaken existing invariants.
- A validator that converts a failure to a warning is forbidden.

### 2.3 May add contract tests

- Contract tests per D18 are added to the canonical test suite.
- The tests are the architectural acceptance tier.

### 2.4 May introduce temporary legacy → canonical adapters

- Adapters are always `LEGACY → CANONICAL`, never `CANONICAL ↔ LEGACY` (INV-B15).
- Each adapter has an explicit owner, retirement condition, and module-level `LEGACY ADAPTER` marker.
- A bidirectional adapter is forbidden.

### 2.5 May migrate semantic properties

- Semantic operators from Substrate B evolution are selectively absorbed into `evolution/core/operations.py` (R1-D.3).
- The 9 BIRNodeTypes are read as references and absorbed into the canonical CompilerIR contract where genuinely semantic (R1-D.2).
- The constitutional EIR's useful schema fields are absorbed into the canonical `EvolutionRecord` (R1-D.3).
- The selective absorption is per the D15 compatibility matrix.

### 2.6 May create canonical modules for new contracts

- The canonical CompilerIR module is created in R1-D.2.
- The canonical ArchitectureCandidate module is formalized in R1-D.3.
- The canonical EvolutionRecord module is created in R1-D.3.
- The canonical ArtifactSet module is created in R1-D.5.

### 2.7 May correct defects in the canonical runtime

- The Gen-C `self.write_files()` defect is corrected in R1-E.7 (return `ArtifactSet`; packager writes). If correction is not feasible, the backend is retired.
- The Gen-C fail-open verification pass is adapted in R1-E.1 to the canonical contract. If adaptation is not feasible, the pass is retired.

### 2.8 May demote backend classifications

- `python-fastapi` and `rust-axum` may be demoted from `BEHAVIORAL` to `STRUCTURAL` until evidence supports `BEHAVIORAL` (R1-E.8).
- The demotion does not weaken verification; it reflects the actual evidence.

### 2.9 May preserve the B3-v2 evidence chain

- The B3-v2 evidence chain is preserved unchanged (INV-B13).
- A new campaign identity (R2) is the post-migration certification baseline.

## 3. MAY NOT — Forbidden changes in R1-C / R1-D

### 3.1 May not rewrite B3-v2

- The B3-v2 evidence chain is immutable. R1-B does not alter historical certification evidence.
- A new campaign is **not** a re-run of B3-v2.

### 3.2 May not modify historical certification evidence

- Historical records are not modified, deleted, or rewritten.
- The hash chain is append-only.

### 3.3 May not create bidirectional adapters

- A bidirectional adapter (`CANONICAL ↔ LEGACY`) recreates the dual-source-of-truth problem and is forbidden (INV-B15).
- A legacy implementation that requires bidirectional access is retired, not adapted.

### 3.4 May not introduce another ISR

- There is exactly one authoritative semantic representation of an ISR revision (INV-B01).
- A new ISR package is forbidden.
- A view, projection, or adapter may exist; none may independently define ISR semantics.

### 3.5 May not make BIR canonical

- BIR is a semantic donor, not the implementation.
- Content-hash is added to the canonical CompilerIR, not to BIR.
- BIR is **not** modified to add content-hash.

### 3.6 May not make Gen-C a second compiler runtime

- The 8-pass Gen-C pipeline is the future canonical pipeline **only after** it is adapted to the canonical contracts (R1-E.5).
- During the migration window, the canonical runtime remains the campaign runtime (Substrate A).
- A second runtime is forbidden.

### 3.7 May not alter campaign identity

- The B3-v2 campaign is the historical campaign. R2 is the post-migration certification baseline — a new campaign identity, not an alteration of B3-v2.

### 3.8 May not rerun B3-v2

- B3-v2 is complete. It is not rerun. A new campaign is a new identity.

### 3.9 May not delete legacy components before mapping them

- A legacy component is retired only after:
  1. Its replacement exists.
  2. Its behavior is covered.
  3. Its references are migrated.
  4. Its tests pass.
  5. Its provenance is preserved.
  6. Its rollback is understood.
- A legacy component without an explicit retirement condition (per D17) is forbidden.

### 3.10 May not convert failures to success

- A validation failure is not a warning.
- A verification exception is not `PASS`.
- An unsupported backend capability is not `COMPILATION_OK`.
- Missing evidence is not `CERTIFIED`.
- These are forbidden at the contract surface (D14).

### 3.11 May not introduce a second source of truth

- A second canonical ISR, a second canonical Compiler IR, a second Evolution engine, a second backend protocol, a second RequirementGraph, or a second ProvenanceStore is forbidden.
- A new source of truth is a violation of INV-B01, INV-B04, INV-B05, INV-B08, INV-B14.

### 3.12 May not modify the canonical runtime code during R1-B

- R1-B is contract/governance work only. The canonical runtime code (`isr/core/`, `compiler/`, `evolution/`, `reqgraph/`, `certification/`, `release/evidence/`) is frozen during R1-B.
- Migration begins only after R1-B PASS (per D20).

### 3.13 May not commit code outside the authorized R1-B deliverables during R1-B

- During R1-B, only D01–D20 are committed. No code changes.
- After R1-B PASS, R1-C may begin with explicit authorization.

### 3.14 May not commit to alter C-17 or C-18 in R1

- C-17 (`autonomous-api/` observation lineage) is deferred to R2/R3.
- C-18 (`pyproject.toml` topology) is deferred to post-R1 packaging cleanup.
- These are out of R1 scope.

## 4. The migration window

The migration window is bounded:

- **Begin:** R1-C starts after R1-B PASS (per D20).
- **End:** R1-C ends when all legacy components in D17 are either retired or have explicit retirement conditions that are not yet met (with a recorded plan).

During the migration window, legacy components coexist with canonical components. The coexistence is governed by D17 (legacy boundary specification) and the adapter rule (one-way only).

## 5. Migration step gating

Each R1-C step is gated by:

1. The contract tests for the affected contracts (D18) pass.
2. The 243 Tier A CBC1 tests still pass.
3. The migration step is explicitly authorized by the user.

A migration step that fails any of these gates is paused, not silently fixed.

## 6. Field classification

| Field | Classification |
|---|---|
| May / May not rules | **semantic** (binding rules) |
| Migration window, step gating | **observational metadata** |

## 7. Cross-references

- D02–D17: per-contract and cross-contract specifications.
- D20: R1-B gate report (the gate evaluates these constraints).
- R1-A: canonical substrate decision (the basis for the constraints).

---

*End of D19. The migration constraints specify what R1-C and R1-D may and may not change. They are the binding rules for the migration; they prevent architectural drift and protect the canonical substrate.*
