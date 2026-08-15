# Constitutional Governance (Phase 28 + 28.1)

The platform's constitutional control plane. Evaluation happens **before**
execution and fails closed; every significant action is audited and
reconstructable.

## Layout

| Path | Purpose |
|------|---------|
| `kernel.py` | Facade wiring evaluate → approvals → finalize → audit |
| `schemas.py` | All governance models (ISRs, decisions, approvals, audit, lineage, exceptions) |
| `constitution.py` | Versioned constitutions + invariants |
| `policy_compiler.py` | Policy rule compiler + policy set manager (immutable when active) |
| `compliance.py` | Policy Decision Point (deny overrides, deterministic) |
| `approval_workflow.py` | Approvals: create, decide, timeout (DENY_ON_TIMEOUT default) |
| `audit.py` | Hash-chained append-only audit + decision reconstruction |
| `lineage.py` | Forward/backward artifact lineage |
| `exception_manager.py` | Bounded, scoped, revocable exceptions |
| `default_policies.py` | Default policy packs 001–006 |
| `api/openapi.yaml` | OpenAPI 3.0.3 contract (11 paths, 14 schemas) |
| `dashboard/` | **Milestone 5A** — read-mostly ops console (`service.py`, `console.html`, `render_console.py`) |
| `pep/` | **Phase 28.1 (5B/5C)** — Policy Enforcement Point SDK + evolution promotion guard |
| `docs/phase28_governance_kernel_spec_v0.1.md` | Specification, milestone coverage, DoD |

## Quick facts

- Decisions: `ALLOW`, `DENY`, `REQUIRE_EVIDENCE`, `REQUIRE_APPROVAL`,
  `ALLOW_WITH_CONSTRAINTS` (deny overrides; deterministic ordering).
- Dashboard: read-mostly, kernel-only mutations, AC-1..AC-6 tested.
- PEP: fail-closed errors (`GovernanceDeniedError`, `MissingEvidenceError`,
  `ApprovalRequiredError`, `ConstraintsNotSatisfiedError`,
  `GovernanceUnavailableError`); see `pep/README.md`.
- Test suites: `tests/test_governance_kernel.py` (30), 
  `tests/test_governance_dashboard.py` (9), `tests/test_governance_pep.py` (8).

## Render the console

```bash
python -m constitutional_architecture.governance.dashboard.render_console --demo
```

## Phase 28 closure

Milestones M0–M5 (exceptions + dashboard) and Phase 28.1 (PEP SDK) are
complete. One pre-existing, non-blocking collection error
(`tests/test_end_to_end.py` — `Dependency` import from `isr.model`) is
documented in the spec's closure note and belongs to the ISR boundary.
