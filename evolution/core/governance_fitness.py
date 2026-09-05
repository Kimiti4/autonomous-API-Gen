"""Canonical governance fitness — R1-D.3 migration of F-C10-02.

Canonical equivalent of ``constitutional_architecture.governance.governance_fitness``
and ``constitutional_architecture.governance.governance_design_fitness`` for the
canonical evolution runtime. Operates on plain dicts (no constitutional schema
dependencies) so ``evolution/`` no longer imports from
``constitutional_architecture.governance``.

The six governance dimensions (same vocabulary, same order as constitutional):
  - constitutional_currency
  - compliance_posture
  - exception_hygiene
  - audit_integrity
  - ratification_rigor
  - policy_coverage

Each objective is a float in [0.0, 1.0]. Missing/malformed governance scores
the fail-closed 0.0 vector.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping


OBJECTIVE_CONSTITUTIONAL_CURRENCY: str = "constitutional_currency"
OBJECTIVE_COMPLIANCE_POSTURE: str = "compliance_posture"
OBJECTIVE_EXCEPTION_HYGIENE: str = "exception_hygiene"
OBJECTIVE_AUDIT_INTEGRITY: str = "audit_integrity"
OBJECTIVE_RATIFICATION_RIGOR: str = "ratification_rigor"
OBJECTIVE_POLICY_COVERAGE: str = "policy_coverage"

ALL_OBJECTIVES: tuple[str, ...] = (
    OBJECTIVE_CONSTITUTIONAL_CURRENCY,
    OBJECTIVE_COMPLIANCE_POSTURE,
    OBJECTIVE_EXCEPTION_HYGIENE,
    OBJECTIVE_AUDIT_INTEGRITY,
    OBJECTIVE_RATIFICATION_RIGOR,
    OBJECTIVE_POLICY_COVERAGE,
)

_VOTING_RULE_RIGOR: dict[str, float] = {
    "unanimity": 1.0,
    "weighted_majority": 0.7,
    "simple_majority": 0.5,
}
_SEVERITY_TOLERANCE: dict[str, float] = {
    "low": 1.0,
    "medium": 0.7,
    "high": 0.4,
    "critical": 0.1,
}
_VERSIONING_RIGOR: dict[str, float] = {
    "semver_chain": 1.0,
    "date_based": 0.7,
    "monotonic_counter": 0.5,
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


@dataclass(frozen=True)
class GovernanceFitnessResult:
    """Multi-objective governance fitness signal (canonical)."""

    objectives: Mapping[str, float]
    details: Mapping[str, str]
    evaluated_at: datetime
    composite: float | None = None


class GovernanceDesignFitness:
    """Evaluates a candidate's governance DESIGN as a bounded multi-objective
    fitness signal. Pure and deterministic for a given (design, config).

    Canonical equivalent of the constitutional evaluator. Accepts a plain
    design dict (as produced by ``evolution.core.governance_design``) instead
    of a constitutional ``GovernanceDesignISR``.
    """

    def __init__(
        self, config: GovernanceDesignFitnessConfig | None = None
    ) -> None:
        self._config = config or GovernanceDesignFitnessConfig()

    def evaluate(
        self, design: dict[str, Any], now: datetime | None = None
    ) -> GovernanceFitnessResult:
        now = now or datetime.now(timezone.utc)
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

    def _ratification_rigor(self, design: dict[str, Any]) -> tuple[float, str]:
        voting = _VOTING_RULE_RIGOR.get(str(design.get("voting_rule", "simple_majority")), 0.5)
        quorum = min(1.0, int(design.get("quorum", 1)) / self._config.max_meaningful_quorum)
        stages = min(
            1.0, int(design.get("approval_stage_count", 1)) / self._config.max_meaningful_stages
        )
        score = (voting + quorum + stages) / 3.0
        return score, (
            f"voting={design.get('voting_rule')}:quorum={design.get('quorum')}"
            f":stages={design.get('approval_stage_count')}"
        )

    def _policy_coverage(self, design: dict[str, Any]) -> tuple[float, str]:
        target = self._config.target_policy_rule_count
        count = int(design.get("policy_rule_count", 0))
        coverage = min(1.0, count / target) if target > 0 else 1.0
        posture = (
            1.0 if design.get("fail_closed_default", True) else self._config.permissive_policy_factor
        )
        score = coverage * posture
        return score, (
            f"rules={design.get('policy_rule_count')}:fail_closed={design.get('fail_closed_default')}"
        )

    def _exception_hygiene(self, design: dict[str, Any]) -> tuple[float, str]:
        tolerance = _SEVERITY_TOLERANCE.get(str(design.get("exception_max_severity", "high")), 0.4)
        review = (
            1.0 if design.get("exception_review_required", True) else self._config.no_review_factor
        )
        score = tolerance * review
        return score, (
            f"max_severity={design.get('exception_max_severity')}"
            f":review_required={design.get('exception_review_required')}"
        )

    def _audit_integrity(self, design: dict[str, Any]) -> tuple[float, str]:
        score = (
            1.0 if design.get("audit_chaining_required", True) else self._config.no_audit_floor
        )
        return score, f"audit_chaining_required={design.get('audit_chaining_required')}"

    def _compliance_posture(self, design: dict[str, Any]) -> tuple[float, str]:
        score = (
            1.0 if design.get("compliance_evaluation_required", True)
            else self._config.no_compliance_floor
        )
        return score, (
            f"compliance_required={design.get('compliance_evaluation_required')}"
        )

    def _constitutional_currency(self, design: dict[str, Any]) -> tuple[float, str]:
        score = _VERSIONING_RIGOR.get(str(design.get("versioning_strategy", "semver_chain")), 0.5)
        return score, f"versioning={design.get('versioning_strategy')}"


def to_fitness_objectives(result: GovernanceFitnessResult) -> dict[str, float]:
    """Return the six-objective dict for a fitness result."""
    return dict(result.objectives)


_REQUIRED_DESIGN_KEYS: tuple[str, ...] = ("design_id", "voting_rule")


def _validate_design(design: dict[str, Any]) -> None:
    """Fail-closed validation mirroring the constitutional schema's required
    fields. Raises ValueError on missing/invalid required fields so the
    caller returns the fail-closed 0.0 vector.
    """
    if not isinstance(design, dict) or not design:
        raise ValueError("governance design must be a non-empty dict")
    for key in _REQUIRED_DESIGN_KEYS:
        if key not in design:
            raise ValueError(f"governance design missing required field: {key}")
    if not isinstance(design.get("design_id"), str) or not design["design_id"].strip():
        raise ValueError("governance design_id must be a non-empty string")
    if str(design.get("voting_rule")) not in _VOTING_RULE_RIGOR:
        raise ValueError(f"unknown voting_rule: {design.get('voting_rule')!r}")
    if str(design.get("exception_max_severity", "high")) not in _SEVERITY_TOLERANCE:
        raise ValueError("unknown exception_max_severity")
    if str(design.get("versioning_strategy", "semver_chain")) not in _VERSIONING_RIGOR:
        raise ValueError("unknown versioning_strategy")
    for key in ("quorum", "approval_stage_count"):
        value = design.get(key, 1)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f"governance {key} must be an int >= 1")
    count = design.get("policy_rule_count", 0)
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("governance policy_rule_count must be an int >= 0")


def design_objectives(
    design: dict[str, Any],
    dimension: GovernanceDesignFitness | None = None,
) -> dict[str, float]:
    """Return the six-objective dict for a candidate's expressed governance
    design dict.

    Canonical equivalent of the constitutional helper. Raises ValueError on
    malformed designs so the caller returns the fail-closed 0.0 vector.
    """
    _validate_design(design)
    evaluator = dimension or GovernanceDesignFitness()
    result = evaluator.evaluate(design, datetime.now(timezone.utc))
    return to_fitness_objectives(result)


__all__ = [
    "OBJECTIVE_AUDIT_INTEGRITY",
    "OBJECTIVE_COMPLIANCE_POSTURE",
    "OBJECTIVE_CONSTITUTIONAL_CURRENCY",
    "OBJECTIVE_EXCEPTION_HYGIENE",
    "OBJECTIVE_POLICY_COVERAGE",
    "OBJECTIVE_RATIFICATION_RIGOR",
    "ALL_OBJECTIVES",
    "GovernanceDesignFitness",
    "GovernanceDesignFitnessConfig",
    "GovernanceFitnessResult",
    "design_objectives",
    "to_fitness_objectives",
]
