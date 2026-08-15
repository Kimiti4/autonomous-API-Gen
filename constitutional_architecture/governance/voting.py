"""Phase 28 - Voting subsystem.

Conducts deterministic, fail-closed votes over ApprovalWorkflowISR.
Pure function of ISR inputs plus ballots; emits a VoteOutcome value object
suitable for ratification and audit evidence.

Tally strategies are replaceable per VotingRuleKind (plugin-first): each
rule kind maps to a TallyStrategy implementation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .schemas import ApprovalStageISR, ApprovalWorkflowISR, VotingRuleKind


class VotingError(ValueError):
    """Raised for malformed voting inputs (unknown stage, duplicate voter)."""


@dataclass(frozen=True)
class Ballot:
    ballot_id: str
    stage_id: str
    voter: str
    approve: bool
    cast_at: datetime


@dataclass(frozen=True)
class StageResult:
    stage_id: str
    approved: bool
    votes_for: float
    votes_against: float
    participating: int
    quorum_met: bool
    reason: str


@dataclass(frozen=True)
class VoteOutcome:
    workflow_ref: str
    approved: bool
    decided_at: datetime
    reason: str
    stage_results: tuple[StageResult, ...] = ()


class TallyStrategy(Protocol):
    """Replaceable tallying rule for a single workflow stage."""

    def evaluate(
        self,
        stage: ApprovalStageISR,
        ballots: Sequence[Ballot],
        quorum: int,
    ) -> StageResult: ...


class UnanimityTally:
    """Every participating ballot must approve; any against fails closed."""

    def evaluate(self, stage, ballots, quorum):
        if len(ballots) < quorum:
            return StageResult(stage.stage_id, False, 0.0, 0.0, len(ballots), False, "quorum_not_met")
        votes_for = float(sum(1 for b in ballots if b.approve))
        votes_against = float(len(ballots)) - votes_for
        if votes_against > 0:
            return StageResult(stage.stage_id, False, votes_for, votes_against, len(ballots), True, "unanimity_broken")
        return StageResult(stage.stage_id, True, votes_for, 0.0, len(ballots), True, "unanimous")


class SimpleMajorityTally:
    """Strict majority; ties fail closed (security-by-design)."""

    def evaluate(self, stage, ballots, quorum):
        if len(ballots) < quorum:
            return StageResult(stage.stage_id, False, 0.0, 0.0, len(ballots), False, "quorum_not_met")
        votes_for = float(sum(1 for b in ballots if b.approve))
        votes_against = float(len(ballots)) - votes_for
        approved = votes_for > votes_against
        reason = "simple_majority" if approved else "tie_or_minority"
        return StageResult(stage.stage_id, approved, votes_for, votes_against, len(ballots), True, reason)


class WeightedMajorityTally:
    """Weighted majority using stage.weights (default weight 1.0).
    Requires strictly more than half of participating weight; ties fail closed."""

    def evaluate(self, stage, ballots, quorum):
        if len(ballots) < quorum:
            return StageResult(stage.stage_id, False, 0.0, 0.0, len(ballots), False, "quorum_not_met")
        votes_for = sum(stage.weights.get(b.voter, 1.0) for b in ballots if b.approve)
        votes_against = sum(stage.weights.get(b.voter, 1.0) for b in ballots if not b.approve)
        total = votes_for + votes_against
        approved = total > 0 and votes_for > total / 2
        reason = "weighted_majority" if approved else "weighted_tie_or_minority"
        return StageResult(stage.stage_id, approved, votes_for, votes_against, len(ballots), True, reason)


def default_strategies() -> dict[VotingRuleKind, TallyStrategy]:
    return {
        VotingRuleKind.UNANIMITY: UnanimityTally(),
        VotingRuleKind.SIMPLE_MAJORITY: SimpleMajorityTally(),
        VotingRuleKind.WEIGHTED_MAJORITY: WeightedMajorityTally(),
    }


class VotingSystem:
    """Conducts multi-stage votes. Deterministic and fail-closed:
    deadline expiry, quorum shortfall, stage rejection, and missing
    strategies all produce denial. Malformed ballots raise VotingError
    (no decision is rendered for invalid input)."""

    def __init__(self, strategies: Mapping[VotingRuleKind, TallyStrategy] | None = None) -> None:
        self._strategies: dict[VotingRuleKind, TallyStrategy] = dict(strategies or default_strategies())

    def conduct_vote(
        self,
        workflow: ApprovalWorkflowISR,
        ballots: Sequence[Ballot],
        now: datetime,
    ) -> VoteOutcome:
        if workflow.deadline is not None and now > workflow.deadline:
            return VoteOutcome(workflow.workflow_id, False, now, "deadline_expired")
        known_stages = {stage.stage_id: stage for stage in workflow.stages}
        if not known_stages:
            return VoteOutcome(workflow.workflow_id, False, now, "workflow_has_no_stages")

        ballots_by_stage = self._group_valid_ballots(workflow, ballots, known_stages)
        results: list[StageResult] = []
        for stage in workflow.stages:  # declared order
            strategy = self._strategies.get(stage.rule)
            if strategy is None:
                return VoteOutcome(
                    workflow.workflow_id, False, now,
                    f"no_strategy_for_rule:{stage.rule.value}", tuple(results),
                )
            result = strategy.evaluate(stage, ballots_by_stage.get(stage.stage_id, ()), workflow.quorum)
            results.append(result)
            if not result.approved:
                return VoteOutcome(
                    workflow.workflow_id, False, now,
                    f"stage_rejected:{stage.stage_id}:{result.reason}", tuple(results),
                )
        return VoteOutcome(workflow.workflow_id, True, now, "all_stages_approved", tuple(results))

    @staticmethod
    def _group_valid_ballots(
        workflow: ApprovalWorkflowISR,
        ballots: Sequence[Ballot],
        known_stages: dict[str, ApprovalStageISR],
    ) -> dict[str, list[Ballot]]:
        valid: dict[str, list[Ballot]] = {}
        seen: set[tuple[str, str]] = set()
        # Sort before grouping so the outcome is independent of ballot order.
        for ballot in sorted(ballots, key=lambda b: (b.stage_id, b.ballot_id)):
            if ballot.stage_id not in known_stages:
                raise VotingError(f"unknown_stage:{ballot.stage_id}")
            key = (ballot.stage_id, ballot.voter)
            if key in seen:
                raise VotingError(f"duplicate_voter:{ballot.voter}:stage:{ballot.stage_id}")
            if workflow.deadline is not None and ballot.cast_at > workflow.deadline:
                continue  # late ballots are ignored, never counted
            seen.add(key)
            valid.setdefault(ballot.stage_id, []).append(ballot)
        return valid
