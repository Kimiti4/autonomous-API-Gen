# FS-00 Checkpoint CP067-W07 — ADR-R1-03 Bridge Semantic Evidence

**Status:** **`PARTIAL_EVIDENCE`** — ADR-R1-03 minimum bridge set (`B-03`…`B-09`) registered with lossiness + verification metadata; independent B-04 oracle + B-07 cross-domain fail-closed enforced on Payroll slice.

| Item | Path |
| --- | --- |
| Contracts | `certification/bridges/transformation_contracts.py` |
| Lossiness policy | `certification/bridges/lossiness_policy.py` |
| IV harness | `certification/isr_independent_verification/w07_bridge_semantic_evidence.py` |
| Evidence | `release/evidence/cp067_w07_bridge_semantic_evidence_report.json` |
| Tests | `tests/bridges/test_adr_r1_03_bridge_registry.py`, `tests/conformance/test_cp067_w07_bridge_semantic_evidence.py` |
| W10 gate | `W07-ADR-R1-03-BRIDGE-EVIDENCE` in `wave10_integration_gate.py` |

**Not claimed:** all ≥22 CP067 bridges contracted, B-03 synthesis obligation replay on every workload, B-08/B-09 governed EngISR promotion, universal semantic equivalence.

**CP068:** unchanged — `CP068_CONDITIONAL_ISOLATED_TESTING_ONLY`.

**Note:** CP067-R1 register lists R1-W07 as evidence-graph identity (ISR-009 P2); this checkpoint delivers the **ADR-R1-03 bridge-evidence slice** requested for semantic-equivalence governance.
