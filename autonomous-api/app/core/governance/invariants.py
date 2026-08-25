"""Governance invariant enforcement (§2.5, G-1..G-7).

Each invariant raises GovernanceInvariantError on violation. The subsystem
calls these BEFORE appending events — the event log only ever contains
invariant-satisfying facts.
"""
from __future__ import annotations

from app.core.contracts.governance import (
    CouncilComposition,
    GateOutcome,
    GateStatus,
    GovernanceDecision,
    GovernanceGate,
    is_legal_transition,
    required_gate_categories,
)

EXECUTIVE_ID = "executive"


class GovernanceInvariantError(Exception):
    """Raised when a command would violate a governance invariant (G-x)."""


def check_g1_transition_legality(decision: GovernanceDecision) -> None:
    """G-1: fromState must be current; toState must be the next legal state."""
    if decision.fromState == decision.toState:
        raise GovernanceInvariantError(
            "G-1 violated: fromState == toState (%s)" % decision.fromState
        )
    if not is_legal_transition(decision.fromState, decision.toState):
        raise GovernanceInvariantError(
            "G-1 violated: %s -> %s is not the next legal lifecycle step"
            % (decision.fromState, decision.toState)
        )


def check_g2_gates_satisfied(
    decision: GovernanceDecision,
    gate_outcomes: list[GateOutcome],
    gates_registry: list[GovernanceGate],
) -> None:
    """G-2: an approving transition-authorizing decision requires every
    gate guarding that transition to be passed or waived."""
    if not (decision.verdict == "approve" and decision.authorizesTransition):
        return

    required_categories = required_gate_categories(
        decision.fromState, decision.toState
    )
    guarding = [
        g for g in gates_registry
        if any(
            t.fromState == decision.fromState and t.toState == decision.toState
            for t in g.guards
        )
    ]
    # Gates registered with matching category also guard by category.
    guarding_ids = {g.gateId for g in guarding}
    for outcome in gate_outcomes:
        if (
            outcome.candidateId == decision.candidateId
            and outcome.status in ("passed", "waived")
        ):
            guarding_ids.discard(outcome.gateId)

    missing = sorted(guarding_ids)
    if not required_categories:
        return  # no gates defined for this transition → nothing to satisfy
    if missing:
        raise GovernanceInvariantError(
            "G-2 violated: transition %s->%s requires gates "
            "%s to be passed/waived; outstanding: %s"
            % (decision.fromState, decision.toState,
               required_categories, missing)
        )


def check_g3_waiver_accountability(outcome: GateOutcome) -> None:
    """G-3: a waived gate requires non-null waivedBy."""
    if outcome.status == "waived" and not outcome.waivedBy:
        raise GovernanceInvariantError(
            "G-3 violated: waived gate %s requires waivedBy"
            % outcome.gateId
        )


def check_g5_decider_authorization(
    decided_by: list[str], council: CouncilComposition
) -> None:
    """G-5: deciders must be council members or the Executive."""
    member_ids = {m.memberId for m in council.members}
    allowed = member_ids | {EXECUTIVE_ID}
    unauthorized = [d for d in decided_by if d not in allowed]
    if unauthorized:
        raise GovernanceInvariantError(
            "G-5 violated: deciders not on council/executive: %s"
            % unauthorized
        )


def check_g7_quorum_weight(
    decided_by: list[str],
    council: CouncilComposition,
    threshold: float,
) -> None:
    """G-7: approving decisions need combined votingWeight >= threshold."""
    weights = {
        m.memberId: m.votingWeight for m in council.members
    }
    total = sum(weights.get(d, 0.0) for d in decided_by)
    if total < threshold:
        raise GovernanceInvariantError(
            "G-7 violated: voting weight %.2f < quorum threshold %.2f"
            % (total, threshold)
        )