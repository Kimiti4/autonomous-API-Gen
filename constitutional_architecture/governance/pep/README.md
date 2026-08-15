# Policy Enforcement Point SDK (Phase 28.1)

A minimal, dependency-free enforcement adapter that turns the Phase 28
Governance Kernel into a Policy Enforcement Point every subsystem can use.
**Any subsystem can become a PEP with minimal code.**

## Enforcement contract

| Kernel decision        | PEP behavior                                                        |
| ---------------------- | ------------------------------------------------------------------- |
| `DENY`                 | `GovernanceDeniedError`; nothing may proceed, no ISR mutation       |
| `REQUIRE_EVIDENCE`     | `MissingEvidenceError`; **no approval-request workaround**          |
| `REQUIRE_APPROVAL`     | `ApprovalRequiredError`; action paused in PENDING; no ISR mutation  |
| `ALLOW_WITH_CONSTRAINTS` | `ConstraintsNotSatisfiedError` unless the handler satisfies them  |
| `ALLOW`                | proceed; caller records decision ref, audit, lineage, rollback      |
| kernel unreachable     | `GovernanceUnavailableError` — fail closed, never proceed           |

## Modules

- `errors.py` — structured enforcement errors (`GovernanceEnforcementError`
  base + five concrete errors), each carrying `decision_id`, `reason`, and
  the original request for reconstruction.
- `client.py` — thin PEP client over the kernel evaluation/approval flow,
  plus `autonomous_agent()` for the evolution coordinator actor shape.
- `context.py` — `EvolutionContextBuilder`, the declarative context for
  evolution promotions (parent hash, rollback plan, verification/
  simulation status, fitness evaluation id, mutation type, audit
  commitment, evidence refs).
- `enforcement.py` — `PEPEnforcer`, the decision-to-behavior mapper and
  `EnforcementResult`.
- `decorators.py` — `@governed_action` for wrapping subsystem methods.
- `evolution_guard.py` — `EvolutionPromotionGuard`, the promotion-boundary
  adapter for the Evolution Engine (Phase 21 seam).

## Quick start

```python
from constitutional_architecture.governance.pep import (
    PEPEnforcer,
    GovernanceClient,
    autonomous_agent,
    GovernanceDeniedError,
)

enforcer = PEPEnforcer(GovernanceClient(kernel))
try:
    result = enforcer.enforce(
        subject_type="EVOLUTION_PROPOSAL",
        subject_id="proposal_42",
        action="PROMOTE",
        actor=autonomous_agent("evolution_agent_01"),
        evidence_refs=["verification_report", "simulation_report"],
        context={"parent_isr_hash": "h_41", "has_rollback_plan": True,
                 "verification_status": "passed", "audit_commitment": True},
        on_allowed=lambda r: perform_promotion(r),
    )
except GovernanceDeniedError as exc:
    abort(exc.reason)
```

## Approval flow (autonomous subsystems)

A `REQUIRE_APPROVAL` decision pauses the action. The subsystem records the
PENDING state; a human/role approver acts through the kernel (via the
Dashboard service); the subsystem then calls `finalize()` and **re-runs the
enforcement** before acting:

```python
try:
    enforcer.enforce(...)          # raises ApprovalRequiredError
except ApprovalRequiredError as exc:
    pending = exc.approval_ids
    # ...wait for approvals (kernel.submit_approval by a human)...
    final = client.finalize(decision_or_pending, ...)
    enforcer.enforce(...)          # now ALLOW, proceed
```

## Evolution promotion guard

`EvolutionPromotionGuard.guard_promote(proposal, actor, promotion_action)`
evaluates a promotion proposal at the boundary, enforces the decision, and
only when allowed invokes `promotion_action` (which applies the ISR
mutation). Lineage (parent -> child, decision ref, approval refs,
**evidence refs**, rollback plan ref) is recorded afterwards. The guard is
an enforcement adapter, not a promotion implementation.

### Rollback execution (Phase 28.1)

If `promotion_action` raises after governance allowed the promotion, the
guard:

1. executes `rollback_action(payload)` when supplied (rollback plan);
2. records an `ACTION_ROLLED_BACK` audit event (hash-chained) with the
   rollback plan ref and whether rollback actually executed;
3. raises `PromotionExecutionError` carrying the original cause, the
   rollback outcome, and the decision id.

A failed promotion never records success lineage, and the subsystem is
told explicitly that state was reverted (or that it must revert it).

```python
try:
    guard.guard_promote(
        proposal, actor, apply_isr_mutation,
        rollback_action=execute_rollback_plan,
    )
except PromotionExecutionError as exc:
    revert_subsystem_state(exc.rollback_outcome)  # state was/is being reverted
except GovernanceDeniedError as exc:
    abort(exc.reason)
```

### Evidence traceability

Lineage links carry `evidence_refs` (verification report, simulation
report, fitness evaluation, …) so every promotion can be traced back to
the evidence that justified it, end to end.

## Fail-closed guarantee

Any kernel error surfaces as `GovernanceUnavailableError`; no branch of the
enforcer ever treats an error as an allow. When governance is unavailable,
no action proceeds.
