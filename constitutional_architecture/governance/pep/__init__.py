"""
Phase 28.1 — Policy Enforcement Point SDK.

A minimal, dependency-free enforcement adapter that turns the Phase 28
Governance Kernel into a Policy Enforcement Point every subsystem can use.
Any subsystem can become a PEP with a few lines of code:

    from constitutional_architecture.governance.pep import (
        PEPEnforcer, autonomous_agent, GovernanceDeniedError,
    )

    enforcer = PEPEnforcer(GovernanceClient(kernel))
    try:
        result = enforcer.enforce(
            subject_type="EVOLUTION_PROPOSAL",
            subject_id="proposal_42",
            action="PROMOTE",
            actor=autonomous_agent("evolution_agent_01"),
            evidence_refs=["verification_report"],
        )
    except GovernanceDeniedError as exc:
        abort(exc)

Enforcement contract (fail closed):
  DENY                     -> GovernanceDeniedError; no ISR mutation
  REQUIRE_EVIDENCE         -> MissingEvidenceError; no approval workaround
  REQUIRE_APPROVAL         -> ApprovalRequiredError; paused PENDING, no
                              mutation until finalize() + re-evaluation
  ALLOW_WITH_CONSTRAINTS   -> ConstraintsNotSatisfiedError unless the
                              handler satisfies them
  ALLOW                    -> proceed; record decision ref / audit /
                              lineage / rollback
  kernel errors            -> GovernanceUnavailableError; never proceed
"""

from constitutional_architecture.governance.pep.client import (
    EVOLUTION_COORDINATOR_ROLES,
    EVOLUTION_DELEGATED_AUTHORITY,
    GovernanceClient,
    autonomous_agent,
)
from constitutional_architecture.governance.pep.context import (
    EvolutionContextBuilder,
)
from constitutional_architecture.governance.pep.decorators import governed_action
from constitutional_architecture.governance.pep.enforcement import (
    EnforcementContext,
    EnforcementResult,
    PEPEnforcer,
)
from constitutional_architecture.governance.pep.errors import (
    ApprovalRequiredError,
    ConstraintsNotSatisfiedError,
    GovernanceDeniedError,
    GovernanceEnforcementError,
    GovernanceUnavailableError,
    MissingEvidenceError,
)
from constitutional_architecture.governance.pep.evolution_guard import (
    EvolutionPromotionGuard,
)

__all__ = [
    "GovernanceClient",
    "autonomous_agent",
    "EVOLUTION_COORDINATOR_ROLES",
    "EVOLUTION_DELEGATED_AUTHORITY",
    "EvolutionContextBuilder",
    "governed_action",
    "PEPEnforcer",
    "EnforcementContext",
    "EnforcementResult",
    "EvolutionPromotionGuard",
    "GovernanceDeniedError",
    "MissingEvidenceError",
    "ApprovalRequiredError",
    "ConstraintsNotSatisfiedError",
    "GovernanceUnavailableError",
    "GovernanceEnforcementError",
]
