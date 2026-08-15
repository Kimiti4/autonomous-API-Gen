"""
Governance gateway for ecosystem actions.

Provides three implementations of the :class:`GovernanceGateway` contract:

* :class:`StaticGovernanceGateway` — deterministic ALLOW / DENY /
  REQUIRE_APPROVAL for tests and local development.
* :class:`GovernanceKernelGateway` — delegates to a real Phase 28
  ``GovernanceKernel``, projecting its ``Decision`` onto the ecosystem
  ``GovernanceDecision`` **and** routing REQUIRE_APPROVAL decisions through the
  kernel's approval workflow (``create_approvals`` / ``submit_approval``).
* :func:`build_ecosystem_governance_kernel` — factory that builds a kernel with
  an "Ecosystem Constitution" and an activated ecosystem policy set.

:func:`_default_governance_gateway` builds a real kernel gateway when Phase 28
is importable and otherwise falls back to a permissive static gateway so the
ecosystem remains operable offline (fail-open only for the *absence* of a
kernel; a kernel that errors at evaluation is treated as DENY).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Protocol

from pydantic import BaseModel, Field


class GovernanceDecision(BaseModel):
    """Decision returned by the governance gateway."""

    decision: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"]

    reason: str = ""

    approval_ref: Optional[str] = None

    constraints: Dict[str, Any] = Field(default_factory=dict)


class GovernanceGateway(Protocol):
    """Abstract governance gateway."""

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> GovernanceDecision:
        ...


class StaticGovernanceGateway:
    """Static governance gateway for tests and local development."""

    def __init__(
        self,
        decision: Literal["ALLOW", "DENY", "REQUIRE_APPROVAL"] = "ALLOW",
        reason: str = "Static governance decision.",
    ) -> None:
        self._decision = decision
        self._reason = reason

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> GovernanceDecision:
        return GovernanceDecision(
            decision=self._decision,
            reason=self._reason,
        )


_DECISION_MAP = {
    "ALLOW": "ALLOW",
    "DENY": "DENY",
    "REQUIRE_APPROVAL": "REQUIRE_APPROVAL",
    "REQUIRE_EVIDENCE": "REQUIRE_APPROVAL",
    "ALLOW_WITH_CONSTRAINTS": "ALLOW",
}


def _map_phase28_decision(decision_value: str) -> str:
    return _DECISION_MAP.get(decision_value, "DENY")


def _load_phase28():
    from constitutional_architecture.governance.schemas import (
        Actor,
        ActorType,
        ApprovalDecision,
        Decision,
        GovernanceEvaluationRequest,
    )

    return Actor, ActorType, ApprovalDecision, Decision, GovernanceEvaluationRequest


class GovernanceKernelGateway:
    """Governance gateway backed by a real Phase 28 ``GovernanceKernel``.

    Honours the kernel's decision exactly. When the kernel returns
    ``REQUIRE_APPROVAL``, the gateway materializes approval requests on the
    kernel via ``create_approvals`` and exposes them through ``submit_approval``.
    Once all required approvals for an action are submitted and approved, a
    subsequent evaluation short-circuits to ALLOW so the engine can proceed.
    """

    def __init__(self, kernel: object) -> None:
        self.kernel = kernel
        self._pending: Dict[str, List[str]] = {}
        self._approved: set[str] = set()

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> GovernanceDecision:
        if action in self._pending and all(
            aid in self._approved for aid in self._pending[action]
        ):
            return GovernanceDecision(
                decision="ALLOW",
                reason=f"Required approvals satisfied for {action}.",
            )

        try:
            Actor, ActorType, _ApprovalDecision, Decision, GovernanceEvaluationRequest = (
                _load_phase28()
            )
        except Exception:
            return GovernanceDecision(
                decision="ALLOW",
                reason="Phase 28 schemas unavailable; allow by default.",
            )

        actor_id = context.get("actor") or context.get("actor_id") or "ecosystem"
        actor = Actor(actor_id=actor_id, actor_type=ActorType.SERVICE, roles=["ecosystem"])
        evidence_refs = list(context.get("evidence_refs", []))
        clean_context = {
            key: value
            for key, value in context.items()
            if key not in ("actor", "actor_id", "evidence_refs")
        }
        request = GovernanceEvaluationRequest(
            subject_type="ecosystem",
            subject_id=str(context.get("subject_id", action)),
            action=action,
            actor=actor,
            context=clean_context,
            evidence_refs=evidence_refs,
        )

        try:
            decision = self.kernel.evaluate(request)
        except Exception as exc:
            # A kernel that is unreachable at evaluation time fails closed:
            # do not implicitly authorize high-risk ecosystem actions.
            return GovernanceDecision(
                decision="DENY",
                reason=f"Phase 28 evaluation unavailable ({exc}); fail-closed.",
            )

        decision_value = getattr(decision, "decision", None)
        if isinstance(decision_value, Enum):
            decision_value = decision_value.value
        decision_value = str(decision_value or "")

        constraints = getattr(decision, "constraints", None) or {}
        if not isinstance(constraints, dict):
            constraints = {"value": constraints}

        approval_ref: Optional[str] = None
        if decision_value == "REQUIRE_APPROVAL":
            try:
                approval_ids = list(self.kernel.create_approvals(decision))
            except Exception:
                approval_ids = []
            self._pending[action] = approval_ids
            approval_ref = ",".join(approval_ids)
            return GovernanceDecision(
                decision="REQUIRE_APPROVAL",
                reason=getattr(decision, "reason", "") or "Approval required.",
                approval_ref=approval_ref or None,
            )

        return GovernanceDecision(
            decision=_map_phase28_decision(decision_value),
            reason=getattr(decision, "reason", "") or "",
            approval_ref=None,
            constraints=constraints,  # type: ignore[arg-type]
        )

    def submit_approval(
        self,
        approval_id: str,
        actor: str = "ecosystem",
        comments: Optional[str] = None,
    ) -> str:
        try:
            Actor, ActorType, ApprovalDecision, _D, _R = _load_phase28()
        except Exception:
            raise PermissionError("Phase 28 schemas unavailable; cannot submit approval.")

        actor_obj = Actor(  # type: ignore[name-defined]
            actor_id=actor, actor_type=ActorType.SERVICE, roles=["ecosystem_approver"]
        )
        record = self.kernel.submit_approval(
            approval_id,
            ApprovalDecision.APPROVED,
            comments=comments,
            actor=actor_obj,
        )
        status = getattr(record, "status", None)
        status_value = status.value if isinstance(status, Enum) else str(status or "")
        self._approved.add(approval_id)
        return status_value

    def list_pending_approvals(self, action: str) -> List[str]:
        return list(self._pending.get(action, []))


# Canonical high-risk ecosystem actions governed via Phase 28 (spec §2.1).
ECOSYSTEM_GOVERNED_ACTIONS: List[str] = [
    "FEDERATION_TREATY_ACTIVATION",
    "PARTNER_ONBOARDING_HIGH_RISK",
    "CROSS_MARKETPLACE_ROUTING_POLICY_CHANGE",
    "B2B_SLA_PENALTY_ENFORCEMENT",
    "ECOSYSTEM_SUSPENSION",
]


def _allow_rule(action: str, priority: int = 100) -> Dict[str, Any]:
    return {
        "id": f"ecosystem_allow_{action.lower()}",
        "name": f"Allow ecosystem {action}",
        "effect": "ALLOW",
        "subject_types": ["ecosystem"],
        "actions": [action],
        "priority": priority,
    }


def ecosystem_allow_all_rules() -> List[Dict[str, Any]]:
    """Default ecosystem policy: allow all canonical governed actions."""
    return [_allow_rule(action) for action in ECOSYSTEM_GOVERNED_ACTIONS]


def build_ecosystem_governance_kernel(
    rule_definitions: Optional[List[Dict[str, Any]]] = None,
) -> tuple[object, object]:
    """Build a real Phase 28 ``GovernanceKernel`` wired with an ecosystem
    constitution and an activated ecosystem policy set.

    Returns ``(kernel, policy_set)``. ``rule_definitions`` defaults to an
    allow-all ecosystem policy set; supply custom rules (e.g. a DENY rule or a
    REQUIRE_APPROVAL rule with ``required_approvals``) to exercise end-to-end
    policy gating and approval routing.
    """
    from constitutional_architecture.governance.kernel import GovernanceKernel

    kernel = GovernanceKernel()

    constitution = kernel.create_constitution(
        name="Ecosystem Constitution",
        policy_domains=["ecosystem"],
    )
    kernel.activate_constitution(constitution.id)

    rules = (
        list(rule_definitions)
        if rule_definitions is not None
        else ecosystem_allow_all_rules()
    )
    policy_set = kernel.create_policy_set(
        name="ecosystem-default",
        constitution_id=constitution.id,
        constitution_version=constitution.version,
        rule_definitions=rules,
    )
    kernel.activate_policy_set(policy_set.id)

    return kernel, policy_set


def _default_governance_gateway() -> "GovernanceGateway":
    """Production default: a real Phase 28 kernel gateway when importable,
    otherwise a permissive static gateway (offline-safe)."""
    try:
        kernel, _policy_set = build_ecosystem_governance_kernel()
    except Exception:
        return StaticGovernanceGateway(
            decision="ALLOW",
            reason="Phase 28 GovernanceKernel unavailable; default allow.",
        )
    return GovernanceKernelGateway(kernel)
