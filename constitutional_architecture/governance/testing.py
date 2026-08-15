"""
Phase 28 — test fixtures (shared).

A ready-to-use governance kernel with a default constitution and all six
default policy packs active, plus a parameterized variant for tests that
need to exclude packs. Lives in the package (not tests/) so test modules
can import it regardless of which root pytest is invoked from.
"""

from __future__ import annotations

from typing import Iterable

from constitutional_architecture.governance import ALL_POLICY_PACKS
from constitutional_architecture.governance.kernel import GovernanceKernel
from constitutional_architecture.governance.schemas import (
    Actor,
    ActorType,
    GovernanceEvaluationRequest,
    Invariant,
)

EVOLUTION_AGENT_ACTOR = Actor(
    actor_type=ActorType.AUTONOMOUS_AGENT,
    actor_id="evolution_agent_01",
    roles=["evolution_proposer", "evolution_coordinator"],
    delegated_authority=["propose_isr_changes"],
)


def make_kernel(
    *,
    excluded_packs: Iterable[str] = (),
) -> GovernanceKernel:
    kernel = GovernanceKernel()
    constitution = kernel.create_constitution(
        name="Platform Constitution",
        description="Root constitutional governance.",
        policy_domains=[
            "isr_integrity",
            "autonomy_bounds",
            "safety_verification",
            "reversibility",
            "auditability",
        ],
        invariants=[
            Invariant(
                id="inv_immutable_isr",
                name="ISR artifacts must be immutable",
            )
        ],
    )
    kernel.activate_constitution(constitution.id)
    excluded = set(excluded_packs)
    for pack_name, rules in ALL_POLICY_PACKS.items():
        if pack_name in excluded:
            continue
        policy_set = kernel.create_policy_set(
            name=pack_name,
            constitution_id=constitution.id,
            constitution_version=constitution.version,
            rule_definitions=rules,
        )
        kernel.activate_policy_set(policy_set.id)
    return kernel


def make_approval_request(**overrides) -> GovernanceEvaluationRequest:
    """An evolution promotion request that lands on REQUIRE_APPROVAL with
    the default packs (evidence present, rollback + audit commitment set)."""
    params = dict(
        subject_type="EVOLUTION_PROPOSAL",
        subject_id="proposal_1",
        action="PROMOTE",
        actor=EVOLUTION_AGENT_ACTOR,
        context={
            "environment": "staging",
            "has_rollback_plan": True,
            "verification_status": "passed",
            "parent_hash": "h_parent",
            "content_hash": "h_content",
            "audit_commitment": True,
        },
        evidence_refs=["verification_report", "simulation_report"],
    )
    params.update(overrides)
    return GovernanceEvaluationRequest(**params)
