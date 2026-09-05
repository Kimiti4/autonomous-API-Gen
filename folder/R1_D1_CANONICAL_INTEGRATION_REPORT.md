# R1_D1_CANONICAL_INTEGRATION_REPORT (R1-D.1 D7)

**Status:** R1-D.1 Deliverable D7. Canonical integration report. Index: `folder/R1_D1_ISR_MIGRATION_MAP.md` (D4), `folder/CONTRACT_CanonicalISR.md` (D03).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; R1-C C01–C12; the R1-D.1 master prompt.

---

## 1. Purpose

Document the before/after state of the canonical ISR after R1-D.1. The R1-D.1 master prompt requires: "Document: before, after, canonical authority, adapters, consumer changes, invariants, remaining boundaries."

---

## 2. Before

| Aspect | Value |
|---|---|
| Canonical ISR | `isr/core/` (9 NodeType, 8 EdgeType, frozen Pydantic, SHA-256, 25 FORBIDDEN_IMPLEMENTATION_TERMS) |
| NodeType count | 9 |
| EdgeType count | 8 |
| FORBIDDEN lists | 1 (`FORBIDDEN_IMPLEMENTATION_TERMS`, 25 terms) |
| Security-by-design docstrings | None |
| Testing-mechanism check | None |
| CAPABILITY.name requirement | None |
| INFRASTRUCTURE_TARGET.target requirement | None |
| Constitutional ISR semantics | 12 validators in `constitutional_architecture/isr/semantics/*` (not in canonical runtime) |
| Test count | 258 (243 Tier A + 15 R1-C) |
| R1-D.1 test count | 0 |
| HEAD | `0f0c4d4` (R1-C gate) |

---

## 3. After

| Aspect | Value |
|---|---|
| Canonical ISR | `isr/core/` (unchanged taxonomy: 9 NodeType, 8 EdgeType) |
| NodeType count | 9 (unchanged) |
| EdgeType count | 8 (unchanged) |
| FORBIDDEN lists | 2 (`FORBIDDEN_IMPLEMENTATION_TERMS` 25 terms + `TESTING_MECHANISM_TERMS` 10 terms) |
| Security-by-design docstrings | **ADDED** on `NodeType.SECURITY_POLICY` and `EdgeType.SECURED_BY` |
| Testing-mechanism check | **ADDED** — all node properties checked for testing-mechanism contamination |
| CAPABILITY.name requirement | **DEFERRED** (breaking change; not in R1-D.1) |
| INFRASTRUCTURE_TARGET.target requirement | **DEFERRED** (breaking change; not in R1-D.1) |
| Constitutional ISR semantics | 5 MIGRATE (3 done, 2 deferred), 2 ALREADY CANONICAL, 7 DEFER |
| Test count | 302 (243 Tier A + 15 R1-C + 23 v12 + 21 R1-D.1) |
| R1-D.1 test count | 21 (5 M-01, 5 M-02, 5 M-03, 2 integration, 4 canonical authority) |

---

## 4. Canonical authority

| Surface | Before | After |
|---|---|---|
| Canonical ISR | `isr/core/` | `isr/core/` (unchanged) |
| Canonical NodeType | 9 values | 9 values (unchanged) |
| Canonical EdgeType | 8 values | 8 values (unchanged) |
| Canonical identity | SHA-256 (deterministic) | SHA-256 (unchanged) |
| Canonical serialization | Canonical JSON (sorted keys) | Canonical JSON (unchanged) |
| Canonical provenance | `Provenance` (frozen Pydantic) | `Provenance` (unchanged) |
| Canonical fail-closed | `validate_invariants` raises | `validate_invariants` raises + new testing-mechanism check |
| Forbidden terms | 25 implementation terms | 25 implementation + 10 testing-mechanism terms |
| Security spine | `SECURED_BY` edge | `SECURED_BY` edge + security-by-design docstring |
| Requirement spine | `REQUIREMENT_REF` + `ref_id` | `REQUIREMENT_REF` + `ref_id` + testing-mechanism check on `ref_id` |

---

## 5. Adapters

R1-D.1 does **not** introduce any new adapter. The constitutional ISR semantics are migrated directly into `isr/core/`, not through an adapter layer. This is consistent with the R1-A decision: "BIR is a semantic donor, not the implementation"; the constitutional ISR is also a semantic donor, not a parallel runtime.

The R1-D.1 migration is **additive**, not an adapter:
- `TESTING_MECHANISM_TERMS` added to `isr/core/invariants.py`.
- Testing-mechanism check added to `validate_invariants`.
- Security-by-design docstrings added to `NodeType.SECURITY_POLICY` and `EdgeType.SECURED_BY`.

No legacy ISR adapter is created. The constitutional ISR implementations are on a retirement path (R1-D.5).

---

## 6. Consumer changes

| Consumer | Before | After |
|---|---|---|
| 17 canonical ISR consumers | Working | Working (unchanged) |
| 5 constitutional ISR consumers | Working in constitutional substrate | Still working in constitutional substrate; classified for retirement (R1-D.5) |
| Campaign runtime (Tier A) | 243/243 pass | 243/243 pass (unchanged) |
| R1-C adapter tests | 15/15 pass | 15/15 pass (unchanged) |
| v12 tests | 23/23 pass | 23/23 pass (unchanged) |
| R1-D.1 tests | N/A | 21/21 pass (NEW) |
| **Total** | **281** | **302** |

---

## 7. Invariants

### 7.1 New invariants (R1-D.1)

- **M-01:** `REQUIREMENT_REF` nodes with testing-mechanism terms in their properties (including `ref_id`) are rejected with `ISRInvariantViolation`.
- **M-02:** ALL node types are checked for testing-mechanism terms in their properties and type label. This is a general principle: the canonical ISR is technology-neutral and mechanism-neutral.
- **M-03:** `SECURITY_POLICY` and `SECURED_BY` are documented as the security-by-design spine. The semantic is: security threats are obligations supplied by evolution/architecture selection, not findings from scanners.

### 7.2 Preserved invariants

- No duplicate edge IDs.
- Referential integrity (edge source/target must exist).
- Edge type compatibility (`EDGE_TYPE_COMPATIBILITY` matrix).
- Implementation leakage (25 forbidden terms).
- `REQUIREMENT_REF.ref_id` must be a non-empty string.
- Content hash determinism (SHA-256 over canonical sorted JSON).

### 7.3 Deferred invariants

- `CAPABILITY.name` (was M-04; deferred to a future R-phase with a proper deprecation period).
- `INFRASTRUCTURE_TARGET.target` (was M-05; deferred).

---

## 8. Remaining boundaries

| Boundary | Status | Action |
|---|---|---|
| Constitutional ISR (`constitutional_architecture/isr/`) | LEGACY; rich model not canonical | **RETIRE** in R1-D.5 (per D17 L01) |
| `UniversalISR` (`constitutional_architecture/core/models/isr.py`) | LEGACY; no canonical consumer | **RETIRE** in R1-D.5 (per D17 L02) |
| Constitutional graph (`isr_graph.py`, `legacy_model.py`, `graph/`) | LEGACY; replaced by canonical | **RETIRE** in R1-D.5 |
| 7 constitutional semantic validators (temporal, migration, reliability, documentation, evolution_policy, decision, application_identity) | DEFER | Not in canonical flat model; deferred to future R-phase |
| Constitutional supporting infrastructure (serialization, versioning, diff, metrics, completeness, types, validation, irr, eir) | DEFER | R1-D.x or R1-E.x |
| `constitutional_architecture/isr/views/*`, `profiles/*` | DEFER | Out of R1 scope |
| `constitutional_architecture/compilers/*` (9 per-category) | LEGACY | **RETIRE** in R1-D.5 (per D17 L10, INV-B14) |

---

## 9. Verdict

R1-D.1 is a **bounded, additive, non-breaking** semantic migration:

- 3 MIGRATE semantics added to `isr/core/` (M-01, M-02, M-03).
- 2 ALREADY CANONICAL semantics documented.
- 2 MIGRATE semantics deferred (M-04, M-05) due to breaking-change risk.
- 7 constitutional semantic validators deferred to future R-phases.
- 5 constitutional ISR implementations on the retirement path (R1-D.5).
- Canonical ISR taxonomy (9 NodeType, 8 EdgeType) unchanged.
- 17 canonical consumers continue to work.
- 302 tests pass (was 281; +21 R1-D.1).
- Tier A baseline (243/243) preserved.
- B3-v2 evidence chain preserved.
- No changes to `certification/`, `release/evidence/`, `compiler/core/`, `evolution/core/`, `reqgraph/`.

---

## 10. Cross-references

- D4: `folder/R1_D1_ISR_MIGRATION_MAP.md`
- D8: `folder/R1_D1_ISR_TEST_REPORT.md` (next)

---

*End of D7. The R1-D.1 canonical integration is verified. 302 tests pass. Tier A preserved. No breaking changes.*
