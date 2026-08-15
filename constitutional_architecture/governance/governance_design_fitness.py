"""Governance Design Fitness — scores a candidate's expressed governance
architecture (``GovernanceDesignISR``) across the SAME six objective names used
by the option-(d) operational governance fitness.

Operational scoring (option d) measures the platform's REALIZED governance
state; design scoring (this module) measures a candidate's DESIGNED governance
architecture. Both emit the identical six-objective vocabulary so the
``GovernanceFitnessBridge`` dimension-set-consistency invariant holds whether a
candidate's governance is scored by design or by realized state.

Heuristics are initial and should be calibrated via the continuous-evolution
loop (production telemetry -> fitness update -> genome refinement).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from constitutional_architecture.governance.governance_fitness import (
    OBJECTIVE_AUDIT_INTEGRITY,
    OBJECTIVE_COMPLIANCE_POSTURE,
    OBJECTIVE_CONSTITUTIONAL_CURRENCY,
    OBJECTIVE_EXCEPTION_HYGIENE,
    OBJECTIVE_POLICY_COVERAGE,
    OBJECTIVE_RATIFICATION_RIGOR,
    GovernanceFitnessResult,
    to_fitness_objectives,
)
from constitutional_architecture.governance.schemas import (
    ExceptionSeverity,
    GovernanceDesignISR,
    VersioningStrategyKind,
    VotingRuleKind,
)

_VOTING_RULE_RIGOR: dict[VotingRuleKind, float] = {
    VotingRuleKind.UNANIMITY: 1.0,
    VotingRuleKind.WEIGHTED_MAJORITY: 0.7,
    VotingRuleKind.SIMPLE_MAJORITY: 0.5,
}
_SEVERITY_TOLERANCE: dict[ExceptionSeverity, float] = {
    ExceptionSeverity.LOW: 1.0,
    ExceptionSeverity.MEDIUM: 0.7,
    ExceptionSeverity.HIGH: 0.4,
    ExceptionSeverity.CRITICAL: 0.1,
}
_VERSIONING_RIGOR: dict[VersioningStrategyKind, float] = {
    VersioningStrategyKind.SEMVER_CHAIN: 1.0,
    VersioningStrategyKind.DATE_BASED: 0.7,
    VersioningStrategyKind.MONOTONIC_COUNTER: 0.5,
}


@dataclass(frozen=True)
class GovernanceDesignFitnessConfig:
    """Tunable heuristics. All objective scores remain bounded in [0.0, 1.0]."""

    max_meaningful_quorum: int = 5
    max_meaningful_stages: int = 3
    target_policy_rule_count: int = 10
    permissive_policy_factor: float = 0.6
    no_review_factor: float = 0.7
    no_audit_floor: float = 0.2
    no_compliance_floor: float = 0.2


class GovernanceDesignFitness:
    """Evaluates a candidate's governance DESIGN as a bounded multi-objective
    fitness signal. Pure and deterministic for a given (design, config)."""

    def __init__(
        self, config: GovernanceDesignFitnessConfig | None = None
    ) -> None:
        self._config = config or GovernanceDesignFitnessConfig()

    def evaluate(
        self, design: GovernanceDesignISR, now: datetime
    ) -> GovernanceFitnessResult:
        objectives: dict[str, float] = {}
        details: dict[str, str] = {}

        score, why = self._ratification_rigor(design)
        objectives[OBJECTIVE_RATIFICATION_RIGOR] = score
        details[OBJECTIVE_RATIFICATION_RIGOR] = why

        score, why = self._policy_coverage(design)
        objectives[OBJECTIVE_POLICY_COVERAGE] = score
        details[OBJECTIVE_POLICY_COVERAGE] = why

        score, why = self._exception_hygiene(design)
        objectives[OBJECTIVE_EXCEPTION_HYGIENE] = score
        details[OBJECTIVE_EXCEPTION_HYGIENE] = why

        score, why = self._audit_integrity(design)
        objectives[OBJECTIVE_AUDIT_INTEGRITY] = score
        details[OBJECTIVE_AUDIT_INTEGRITY] = why

        score, why = self._compliance_posture(design)
        objectives[OBJECTIVE_COMPLIANCE_POSTURE] = score
        details[OBJECTIVE_COMPLIANCE_POSTURE] = why

        score, why = self._constitutional_currency(design)
        objectives[OBJECTIVE_CONSTITUTIONAL_CURRENCY] = score
        details[OBJECTIVE_CONSTITUTIONAL_CURRENCY] = why

        return GovernanceFitnessResult(
            objectives=objectives, details=details, evaluated_at=now, composite=None
        )

    # -- individual objectives --------------------------------------------

    def _ratification_rigor(self, design: GovernanceDesignISR) -> tuple[float, str]:
        voting = _VOTING_RULE_RIGOR[design.voting_rule]
        quorum = min(1.0, design.quorum / self._config.max_meaningful_quorum)
        stages = min(
            1.0, design.approval_stage_count / self._config.max_meaningful_stages
        )
        score = (voting + quorum + stages) / 3.0
        return score, (
            f"voting={design.voting_rule.value}:quorum={design.quorum}"
            f":stages={design.approval_stage_count}"
        )

    def _policy_coverage(self, design: GovernanceDesignISR) -> tuple[float, str]:
        target = self._config.target_policy_rule_count
        coverage = min(1.0, design.policy_rule_count / target) if target > 0 else 1.0
        posture = (
            1.0 if design.fail_closed_default else self._config.permissive_policy_factor
        )
        score = coverage * posture
        return score, (
            f"rules={design.policy_rule_count}:fail_closed={design.fail_closed_default}"
        )

    def _exception_hygiene(self, design: GovernanceDesignISR) -> tuple[float, str]:
        tolerance = _SEVERITY_TOLERANCE[design.exception_max_severity]
        review = (
            1.0 if design.exception_review_required else self._config.no_review_factor
        )
        score = tolerance * review
        return score, (
            f"max_severity={design.exception_max_severity.value}"
            f":review_required={design.exception_review_required}"
        )

    def _audit_integrity(self, design: GovernanceDesignISR) -> tuple[float, str]:
        score = (
            1.0 if design.audit_chaining_required else self._config.no_audit_floor
        )
        return score, f"audit_chaining_required={design.audit_chaining_required}"

    def _compliance_posture(self, design: GovernanceDesignISR) -> tuple[float, str]:
        score = (
            1.0 if design.compliance_evaluation_required
            else self._config.no_compliance_floor
        )
        return score, (
            f"compliance_required={design.compliance_evaluation_required}"
        )

    def _constitutional_currency(self, design: GovernanceDesignISR) -> tuple[float, str]:
        score = _VERSIONING_RIGOR[design.versioning_strategy]
        return score, f"versioning={design.versioning_strategy.value}"


def design_objectives(
    design: GovernanceDesignISR,
    dimension: GovernanceDesignFitness | None = None,
) -> dict[str, float]:
    """Return the six-objective dict for a candidate's expressed governance
    design — the exact shape ``GovernanceFitnessBridge.merge_population``
    consumes.

    ADAPTATION POINT (needs confirmation): per-candidate wiring — how a
    candidate exposes its expressed ``GovernanceDesignISR`` so this helper can
    be invoked per candidate instead of the platform-wide
    ``governance_objectives``. Until the candidate model is confirmed, the
    bridge's evaluate-once-apply-to-all path is the safe default.
    """
    evaluator = dimension or GovernanceDesignFitness()
    result = evaluator.evaluate(design, datetime.now(timezone.utc))
    return to_fitness_objectives(result)


def baseline_governance_design() -> dict[str, Any]:
    """Minimal-viable governance design — the floor every candidate is born under.

    Single source of truth for the governance baseline injected by the evolution
    mutation engine. Returns a fresh dict each call (never shared/mutated).

    Security-by-design fundamentals are maxed so a brand-new architecture never
    starts below the fail-closed gate; amendment rigor, policy breadth and
    exception tolerance start modest so the variation operators
    (``strengthen_governance`` and future templates) have selection headroom to
    strengthen them. Every component clears the 0.2 selection gate with margin
    (lowest is ``policy_coverage`` -> ~0.30).
    """
    return {
        "design_id": "baseline_governance_v1",
        "voting_rule": "simple_majority",
        "quorum": 1,
        "approval_stage_count": 1,
        "policy_rule_count": 3,
        "fail_closed_default": True,
        "exception_max_severity": "high",
        "exception_review_required": True,
        "audit_chaining_required": True,
        "compliance_evaluation_required": True,
        "versioning_strategy": "semver_chain",
    }
