# POST_R1_D_RECONCILIATION_TEST_REPORT (R1-RG-11)

**Status:** R1-RG-11. Tests and evidence. Spec: `folder/postr1d.md` §§30–32.

---

## 1. Baseline (§31)

| Suite | Count | Result |
|---|---|---|
| Tier-A (`tests/cbc1/`) | 243 | PASS |
| R1-C (`tests/r1c/`) | 15 | PASS |
| R1-D.1 (`tests/r1d1/`) | 21 | PASS |
| R1-D.2 (`tests/r1d2/`) | 33 | PASS |
| R1-D.3 (`tests/r1d3/`) | 32 | PASS |
| v12 | 23 | PASS |
| Governance (2 files) | 13 | PASS |
| Reconciliation (`tests/rg/`) | 24 | PASS |
| **Combined** | **404** | **PASS (1 deselected, pre-existing)** |

Expected prior baseline (243/15/21/33/32 = 380): **matched exactly**; reconciliation adds 24. No difference to report (§31). Wall time ~85s. No failures, no skips beyond the pre-existing deselection, no weakened assertions.

## 2. Reconciliation coverage (24 tests)

| Class | Tests | Proven |
|---|---|---|
| Authority (7) | ownership ×4, no-duplicate imports ×2, adapter direction | one authority per layer; no silent promotion |
| Contract composition (5) | ISR→Architecture, Architecture→CompilerIR (mediated), CompilerIR→Backend, Artifact→Verification, Verification→Evolution feedback | forward path executable |
| Identity (4) | candidate, operation, lineage, 4-hash provenance correlation | correlation without guessing |
| Failure (4) | unsupported-capability conformance, ledger-failure→NOT_CERTIFIED, integrity→NOT_CERTIFIED, empty selection | fail-closed layering |
| Lineage (4) | parent→child, artifact→candidate, record→operation, D12 fields pinned | reverse path permitted + preserved |

## 3. Historical integrity (§32)

| Item | Status | Evidence |
|---|---|---|
| B3-v2 | untouched | working tree clean for tracked files; ledger/aggregate hashes unchanged |
| `certification/` | untouched | `git status` clean |
| `release/evidence/` | untouched | `git status` clean |
| Historical ledgers | untouched | append-only; no rewrites |

No mutation of historical evidence: gate requirement met, STOP condition avoided.

---

*End of R1-RG-11.*
