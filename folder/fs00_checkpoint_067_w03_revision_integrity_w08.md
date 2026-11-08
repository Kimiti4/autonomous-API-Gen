# FS-00 Checkpoint CP067-W03 — Revision Integrity (W08 ingress scope)

**Status:** **`PARTIAL_EVIDENCE`** — R1-W03 immutability envelope + digest verification at governed orchestration ingress only (not universal ISR).

| Item | Path |
| --- | --- |
| Core | `isr/core/revision_integrity.py` |
| W08 gate | `certification/orchestration/ingress_revision_integrity_gate.py` |
| HTTP preflight | `tiannara/application/orchestration/production_ingress.py` |
| IV | `certification/isr_independent_verification/w03_revision_integrity_verification.py` |
| Matrix tags | `revision_integrity_w03` on orch-api / orch-dashboard / orchestration-authority |
| Evidence | `release/evidence/cp067_w03_revision_integrity_report.json` |

**W08:** No further W08 expansion in this checkpoint — only W03 enforcement on orchestration ingress rows.

**CP068:** `CP068_CONDITIONAL_ISOLATED_TESTING_ONLY`.
