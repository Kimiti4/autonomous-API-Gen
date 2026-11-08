"""Canonical full-stack orchestration contract (Checkpoint 055)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OrchestrationLifecycleState(str, Enum):
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    REQUIREMENTS_PENDING = "REQUIREMENTS_PENDING"
    REQUIREMENTS_APPROVED = "REQUIREMENTS_APPROVED"
    ISR_PENDING = "ISR_PENDING"
    ISR_VALIDATED = "ISR_VALIDATED"
    PLAN_APPROVED = "PLAN_APPROVED"
    COMPILING = "COMPILING"
    ARTIFACTS_GENERATED = "ARTIFACTS_GENERATED"
    INTEGRATION_VERIFYING = "INTEGRATION_VERIFYING"
    BEHAVIOR_VERIFYING = "BEHAVIOR_VERIFYING"
    SENIOR_REVIEW_PENDING = "SENIOR_REVIEW_PENDING"
    EVIDENCE_REGISTERING = "EVIDENCE_REGISTERING"
    PRODUCT_ACCEPTANCE_PENDING = "PRODUCT_ACCEPTANCE_PENDING"
    AWAITING_GOVERNANCE = "AWAITING_GOVERNANCE"
    CERTIFIED = "CERTIFIED"
    PUBLICATION_AUTHORIZED = "PUBLICATION_AUTHORIZED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class IsrProvenance(str, Enum):
    """How the ISR entered the lifecycle — not claimed as auto-synthesis unless verified."""
    USER_SUPPLIED = "USER_SUPPLIED"
    HUMAN_AUTHORED_IMPORTED = "HUMAN_AUTHORED_IMPORTED"
    AUTO_SYNTHESIZED = "AUTO_SYNTHESIZED"
    HUMAN_APPROVED_SYNTHESIZED = "HUMAN_APPROVED_SYNTHESIZED"
    UNKNOWN = "UNKNOWN"


class RequestKind(str, Enum):
    FULL_STACK_PRODUCT = "FULL_STACK_PRODUCT"
    DIRECT_COMPILE_DEV = "DIRECT_COMPILE_DEV"


VALID_TRANSITIONS: dict[OrchestrationLifecycleState, frozenset[OrchestrationLifecycleState]] = {
    OrchestrationLifecycleState.REQUEST_RECEIVED: frozenset({
        OrchestrationLifecycleState.REQUIREMENTS_PENDING,
        OrchestrationLifecycleState.FAILED,
    }),
    OrchestrationLifecycleState.REQUIREMENTS_PENDING: frozenset({
        OrchestrationLifecycleState.REQUIREMENTS_APPROVED,
        OrchestrationLifecycleState.FAILED,
        OrchestrationLifecycleState.REJECTED,
    }),
    OrchestrationLifecycleState.REQUIREMENTS_APPROVED: frozenset({
        OrchestrationLifecycleState.ISR_PENDING,
        OrchestrationLifecycleState.FAILED,
    }),
    OrchestrationLifecycleState.ISR_PENDING: frozenset({
        OrchestrationLifecycleState.ISR_VALIDATED,
        OrchestrationLifecycleState.FAILED,
        OrchestrationLifecycleState.REJECTED,
    }),
    OrchestrationLifecycleState.ISR_VALIDATED: frozenset({
        OrchestrationLifecycleState.PLAN_APPROVED,
        OrchestrationLifecycleState.FAILED,
    }),
    OrchestrationLifecycleState.PLAN_APPROVED: frozenset({
        OrchestrationLifecycleState.COMPILING,
        OrchestrationLifecycleState.FAILED,
    }),
    OrchestrationLifecycleState.COMPILING: frozenset({
        OrchestrationLifecycleState.ARTIFACTS_GENERATED,
        OrchestrationLifecycleState.FAILED,
    }),
    OrchestrationLifecycleState.ARTIFACTS_GENERATED: frozenset({
        OrchestrationLifecycleState.INTEGRATION_VERIFYING,
        OrchestrationLifecycleState.FAILED,
    }),
    OrchestrationLifecycleState.INTEGRATION_VERIFYING: frozenset({
        OrchestrationLifecycleState.BEHAVIOR_VERIFYING,
        OrchestrationLifecycleState.FAILED,
    }),
    OrchestrationLifecycleState.BEHAVIOR_VERIFYING: frozenset({
        OrchestrationLifecycleState.SENIOR_REVIEW_PENDING,
        OrchestrationLifecycleState.FAILED,
        OrchestrationLifecycleState.REJECTED,
    }),
    OrchestrationLifecycleState.SENIOR_REVIEW_PENDING: frozenset({
        OrchestrationLifecycleState.EVIDENCE_REGISTERING,
        OrchestrationLifecycleState.PRODUCT_ACCEPTANCE_PENDING,
        OrchestrationLifecycleState.FAILED,
        OrchestrationLifecycleState.REJECTED,
    }),
    OrchestrationLifecycleState.EVIDENCE_REGISTERING: frozenset({
        OrchestrationLifecycleState.PRODUCT_ACCEPTANCE_PENDING,
        OrchestrationLifecycleState.AWAITING_GOVERNANCE,
        OrchestrationLifecycleState.FAILED,
    }),
    OrchestrationLifecycleState.PRODUCT_ACCEPTANCE_PENDING: frozenset({
        OrchestrationLifecycleState.AWAITING_GOVERNANCE,
        OrchestrationLifecycleState.FAILED,
        OrchestrationLifecycleState.REJECTED,
    }),
    OrchestrationLifecycleState.AWAITING_GOVERNANCE: frozenset({
        OrchestrationLifecycleState.CERTIFIED,
        OrchestrationLifecycleState.FAILED,
        OrchestrationLifecycleState.REJECTED,
    }),
    OrchestrationLifecycleState.CERTIFIED: frozenset({
        OrchestrationLifecycleState.PUBLICATION_AUTHORIZED,
        OrchestrationLifecycleState.FAILED,
    }),
    OrchestrationLifecycleState.PUBLICATION_AUTHORIZED: frozenset({
        OrchestrationLifecycleState.PUBLISHED,
        OrchestrationLifecycleState.FAILED,
    }),
}


TERMINAL_STATES = frozenset({
    OrchestrationLifecycleState.PUBLISHED,
    OrchestrationLifecycleState.FAILED,
    OrchestrationLifecycleState.REJECTED,
})


def assert_transition(
    current: OrchestrationLifecycleState,
    nxt: OrchestrationLifecycleState,
) -> None:
    if current in TERMINAL_STATES:
        raise ValueError(f"orchestration-terminal:{current.value}")
    allowed = VALID_TRANSITIONS.get(current, frozenset())
    if nxt not in allowed:
        raise ValueError(
            f"orchestration-invalid-transition:{current.value}->{nxt.value}"
        )


@dataclass(frozen=True)
class FullStackOrchestrationRequest:
    """Canonical governed full-stack request."""

    workload_id: str
    request_kind: RequestKind = RequestKind.FULL_STACK_PRODUCT
    frontend_backend_id: str = "python-fastapi"
    frontend_id: str = "react-vite"
    optional_rust: bool = True
    populate_senior_dimensions: bool = False
    generator_id: str = "esap-generator"
    reviewer_id: str = "senior-engineering-reviewer"
    verifier_id: str = "independent-verifier"
    run_id: str = ""
    lineage: dict[str, str] = field(default_factory=dict)
    isr_source_mode: str = "human_baseline"
    synthesis_binding_digest: str = ""
    synthesis_run_id: str = ""
    isr_ingress_authority: str = "isr.core.revision"
    governed_lineage_ref: str = ""
    plan_binding_digest: str = ""


@dataclass(frozen=True)
class DirectCompileBoundary:
    """Marks dev-only compile; cannot claim full-stack lifecycle completion."""

    workload_id: str
    completes_lifecycle: bool = False
    max_state: OrchestrationLifecycleState = OrchestrationLifecycleState.ARTIFACTS_GENERATED
