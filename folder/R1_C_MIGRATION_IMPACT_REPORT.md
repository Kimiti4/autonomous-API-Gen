# R1_C_MIGRATION_IMPACT_REPORT (R1-C C11)

**Status:** R1-C Deliverable C11. Migration impact and provenance audit. Index: `folder/R1_C_BOUNDARY_CONTRACTS.md` (C02), `folder/R1_C_ADAPTER_INVENTORY.md` (C01), `folder/R1_B_MIGRATION_CONSTRAINTS.md` (D19).

**Authority:** R1-A canonical substrate decision; R1-B D02–D20; the R1-C master prompt.

---

## 1. Purpose

Audit the migration impact of the R1-C work. For each R1-C change, document:

- What was changed.
- What was not changed.
- What is the migration impact (what is migrated, what is retired, what is deferred).
- What is the provenance impact (what evidence is affected, what is preserved).
- What is the forward impact (what R1-D and R1-E work is unblocked or constrained).

## 2. R1-C changes summary

### 2.1 Governance/boundary artifacts (C01 + C02)

| File | Status | Impact |
|---|---|---|
| `folder/R1_C_ADAPTER_INVENTORY.md` | NEW (committed `2e2944b`) | 70 crossings classified; the implementation map for R1-C and R1-D. |
| `folder/R1_C_BOUNDARY_CONTRACTS.md` | NEW (committed `2e2944b`) | 11 boundary contracts defined; the contract surface for R1-C adapters. |

**Impact:** These are governance/architecture documents. They do not modify runtime code. They establish the boundary contracts that C03–C12 implement.

### 2.2 ADAPTER-ARTIFACT-001 (C06)

| File | Status | Impact |
|---|---|---|
| `constitutional_architecture/compiler/backends/fastapi_backend.py:85` | MODIFIED (one line removed: `self.write_files()`) | The Gen-C FastAPI backend no longer writes to the filesystem inside `compile()`. The backend now returns an `ArtifactSet` via `BackendResult(artifacts=...)`, which is the canonical contract surface. The `write_files()` method itself is preserved as a utility for the packager. |

**Impact:** This is a **bounded, non-canonical change**. It does not affect the canonical campaign runtime (`certification/`, `release/evidence/`, `isr/core/`, `compiler/core/`, `reqgraph/`, `evolution/core/`). It brings the Gen-C backend into compliance with INV-B09 (ArtifactSet is the generated-software boundary; no backend filesystem emission inside `compile()`).

### 2.3 Adapter contract tests (C08)

| File | Status | Impact |
|---|---|---|
| `tests/r1c/__init__.py` | NEW | Package marker for the R1-C test tier. |
| `tests/r1c/test_artifact_adapter.py` | NEW (15 tests) | Verifies ADAPTER-ARTIFACT-001: no filesystem write in `compile()`, ArtifactSet emission, determinism, packager separation, one-way boundary. |

**Impact:** A new test tier, orthogonal to the 243 Tier A CBC1 tests and the 40 Tier C certification tests. All 15 tests pass. The canonical campaign runtime is unaffected.

## 3. What was NOT changed

Per the R1-C spec's repo safety rules, the following were **NOT** changed:

| Surface | Status | Reason |
|---|---|---|
| `certification/` | **FROZEN** | R1-C spec §22: "Do not modify certification/". Historical evidence is immutable. |
| `release/evidence/` | **FROZEN** | R1-C spec §22: "Do not modify release/evidence/". B3-v2 evidence is immutable. |
| `isr/core/` | **FROZEN** | The canonical ISR is unchanged; no new ISR adapter required at this time (C03 deferred to R1-D.1). |
| `compiler/core/` | **FROZEN** | The canonical compiler substrate is unchanged; no new Compiler IR adapter required at this time (C04 deferred to R1-D.2). |
| `reqgraph/core/` | **FROZEN** | The canonical RequirementGraph is unchanged. |
| `evolution/core/` | **FROZEN** | The canonical evolution is unchanged; the 2 findings (F-C10-01, F-C10-02) are REPORTED but not repaired. The governance fitness migration is R1-D.3 work. |
| `tests/cbc1/` | **FROZEN** | Tier A tests are unchanged. 243/243 pass. |
| B3-v2 evidence chain | **PRESERVED** | No rerun; no rewriting. |
| `prefull.md`, `masterprompt.md`, `phase0.md` | **UNCHANGED** | User inputs; not touched. |

## 4. Migration impact (what is migrated, retired, deferred)

### 4.1 Migrated in R1-C

| Item | From | To | Status |
|---|---|---|---|
| `self.write_files()` side effect in Gen-C backend's `compile()` | Inside `compile()` (filesystem emission) | Outside `compile()` (packager's `write_files()` call) | **MIGRATED** (ADAPTER-ARTIFACT-001) |

### 4.2 Retired in R1-C

No retirements in R1-C. The RETIRE items in D17 L01–L14 are R1-D.5 work. The dead-code bridge (`RETIRE-CBRIDGE-001` in C02) is classified for immediate removal but not yet removed in R1-C (R1-D.5 scope).

### 4.3 Deferred in R1-C

| Item | Deferred to | Reason |
|---|---|---|
| C03 (Canonical ISR adapter) | R1-D.1 | The canonical ISR is `isr/core/`; the constitutional ISR semantic validators are MIGRATE_SEMANTICS for R1-D.1, not R1-C. The canonical campaign runtime does not need an ISR adapter at this time. |
| C04 (Canonical Compiler IR adapter) | R1-D.2 | The canonical CompilerIR module is R1-D.2 work. The campaign runtime uses `CompilationPlan` as stabilization. |
| C05 (Evolution/EIR adapter) | R1-D.3 | The canonical EvolutionRecord module is R1-D.3 work. |
| ADAPTER-VERIFY-001 (Gen-C verification pass → canonical Verification) | R1-E.1 | The canonical Verification contract is fail-closed; the Gen-C verification pass is fail-open. The adaptation is canonical-contracts-first (R1-E.1). |
| ADAPTER-VALID-001 (Gen-C validation pass → canonical Validation) | R1-E.2 | Same pattern. |
| ADAPTER-NORM-001 (Gen-C normalization pass → canonical Normalization) | R1-E.4 | Same pattern. |
| ADAPTER-ISR-VALID-001 (constitutional ISR validators → `isr/core/`) | R1-D.1 | MIGRATE_SEMANTICS for R1-D.1. |
| ADAPTER-BIR-001 (BIRNodeTypes → canonical CompilerIR) | R1-D.2 | MIGRATE_SEMANTICS for R1-D.2. |
| ADAPTER-EIR-001 (constitutional EIR → canonical EvolutionRecord) | R1-D.3 | MIGRATE_SEMANTICS for R1-D.3. |
| ADAPTER-CAP-001 (constitutional capabilities → canonical capability resolution) | R1-D.2 | MIGRATE_SEMANTICS for R1-D.2. |
| ADAPTER-LINEAGE-001 (constitutional lineage → canonical lineage, durable) | R1-E.6 | MIGRATE_SEMANTICS for R1-E.6. |
| ADAPTER-EVOL-OP-001 (constitutional mutation operators → canonical Evolution operators) | R1-D.3 | MIGRATE_SEMANTICS for R1-D.3. |
| F-C10-01, F-C10-02 (evolution → constitutional governance bypass) | R1-D.3 | REPORTED in C10; remediation is R1-D.3 (governance fitness migration). |
| RETIRE-CBRIDGE-001 (dead-code `compiler_bridge.py`) | R1-D.5 | Immediate removal is R1-D.5. |
| C-17 (autonomous-api observation lineage) | R2/R3 | DEFERRED per R1-A and D12. |
| C-18 (pyproject.toml topology) | post-R1 packaging cleanup | DEFERRED per R1-A. |

## 5. Provenance impact

| Surface | Provenance impact |
|---|---|
| B3-v2 evidence chain | **PRESERVED.** No rerun, no rewriting. The 443-trial ledger (chain intact) is preserved unchanged. |
| `release/evidence/` | **PRESERVED.** No new non-historical artifacts generated by R1-C. |
| `certification/evidence/` | **PRESERVED.** The `EvidenceLedger` (JSONL, hash-chained, SHA-256) is unchanged. |
| Canonical Runtime Identifiers | **UNCHANGED.** The canonical ISR's content-hash identity, the canonical CompilerIR's content hash, the ArtifactSet's manifest hash — all preserved by the R1-C C06 refactor (the Gen-C backend's change is to a non-canonical file). |
| Cross-contract lineage | **PRESERVED.** The R1-B D13 cross-contract identity model is unchanged. The D13 lineage chain (RequirementGraph → ... → RuntimeObservation) is intact. |

## 6. Forward impact (R1-D and R1-E unblocked)

R1-C unblocks the following R1-D and R1-E work:

- **R1-D.1** (semantic migration of constitutional ISR validators into `isr/core/`) — unblocked by the R1-C boundary (C01 + C02). The 2 findings (F-C10-01, F-C10-02) are also R1-D.3 input.
- **R1-D.2** (canonical CompilerIR module + BIR semantic donor absorption) — unblocked.
- **R1-D.3** (canonical EvolutionRecord + EIR adapter + governance fitness migration) — unblocked. The 2 findings are R1-D.3 input.
- **R1-D.5** (retirement of D17 L01–L14, plus `RETIRE-CBRIDGE-001`) — unblocked.
- **R1-E.1** (canonical Verification contract implementation; adapt Gen-C verification pass) — unblocked.
- **R1-E.2** (canonical Validation pass contract implementation; adapt Gen-C validation pass) — unblocked.
- **R1-E.4** (canonical Normalization contract implementation; adapt Gen-C normalization pass) — unblocked.
- **R1-E.6** (durable lineage) — unblocked.
- **R1-E.7** (canonical CompilerBackend artifact purity for ALL backends; ADAPTER-ARTIFACT-001 is the prototype) — the R1-C C06 refactor is the prototype; R1-E.7 extends the pattern to other backends if needed.

## 7. Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The `constitutional_architecture/tests/test_end_to_end.py` constitutional test breaks | Low | Low | The test calls `write_files(tmpdir)` explicitly (line 514), so the internal removal is safe. The test is NOT in the canonical Tier A. |
| The Gen-C `fastapi_backend.py` is used by some other path I haven't found | Low | Medium | The grep for `FastAPIBackend` and `fastapi_backend` found only constitutional paths. The canonical campaign runtime does NOT use it. |
| The 2 findings (F-C10-01, F-C10-02) cause a runtime issue | Low | Low | The findings are in `evolution/`, not in the campaign runtime path. The 243 Tier A tests confirm the campaign runtime is unaffected. |
| R1-D.3 (governance fitness migration) is harder than expected | Medium | Low | The findings are documented and classified. R1-D.3 can choose to migrate or remove the governance fitness from the canonical evolution. |

## 8. Conclusion

R1-C's migration impact is **bounded and minimal**:

- 1 code change (one line removed from a non-canonical file).
- 15 new tests (a new test tier).
- 2 new governance documents (C01 + C02).
- 2 findings documented for R1-D.
- 0 changes to the canonical campaign runtime.
- 0 changes to historical evidence.
- 0 changes to the canonical contracts (D02–D12).

The R1-C boundary is established. R1-D is unblocked. The canonical runtime is authoritative and verified.

---

*End of C11. R1-C migration impact is bounded. The canonical campaign runtime is preserved. R1-D and R1-E work is unblocked.*
