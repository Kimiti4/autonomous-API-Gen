"""Governance Fitness Dimension - governance health as a multi-objective
fitness signal (the selection half of the governance evolutionary loop).

This module evaluates the platform's constitutional governance state and
projects it into a bounded, multi-objective fitness vector. It reads ONLY
governance ISR (the constitutional source of truth) and never imports the
fitness engine, runtime managers, or any implementation technology.

Constitutional alignment:
  * ISR-only inputs; no dependency on framework or runtime state.
  * Multi-objective by design: the primary output is a vector of bounded
    objectives in [0.0, 1.0]; a scalar composite is opt-in and never the
    primary signal ("avoid relying on a single aggregate score").
  * Independently testable, replaceable, and configuration-injected.
  * Observable-by-design: every objective carries a human-readable rationale.
  * Fail-closed: absence of governance evidence scores low, never defaults to fit.

The framework-neutral result is mapped into the platform's fitness engine by
a thin adapter (see ADAPTER SEAM below). The core never imports that engine.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from constitutional_architecture.governance.schemas import (
    AuditEvidenceISR,
    ChangeLineageISR,
    ComplianceOutcome,
    ComplianceReportISR,
    ConstitutionVersionISR,
    ExceptionSeverity,
    GovernanceExceptionISR,
    PolicyRuleISR,
    VersionStatus,
)

# --- Objective identifiers (stable string keys for fitness-engine interop) ---
OBJECTIVE_CONSTITUTIONAL_CURRENCY = "constitutional_currency"
OBJECTIVE_COMPLIANCE_POSTURE = "compliance_posture"
OBJECTIVE_EXCEPTION_HYGIENE = "exception_hygiene"
OBJECTIVE_AUDIT_INTEGRITY = "audit_integrity"
OBJECTIVE_RATIFICATION_RIGOR = "ratification_rigor"
OBJECTIVE_POLICY_COVERAGE = "policy_coverage"

ALL_OBJECTIVES: tuple[str, ...] = (
    OBJECTIVE_CONSTITUTIONAL_CURRENCY,
    OBJECTIVE_COMPLIANCE_POSTURE,
    OBJECTIVE_EXCEPTION_HYGIENE,
    OBJECTIVE_AUDIT_INTEGRITY,
    OBJECTIVE_RATIFICATION_RIGOR,
    OBJECTIVE_POLICY_COVERAGE,
)

_DEFAULT_SEVERITY_WEIGHTS: Mapping[ExceptionSeverity, float] = {
    ExceptionSeverity.LOW: 0.05,
    ExceptionSeverity.MEDIUM: 0.10,
    ExceptionSeverity.HIGH: 0.20,
    ExceptionSeverity.CRITICAL: 0.40,
}


@dataclass(frozen=True)
class GovernanceFitnessConfig:
    """Tunable parameters. All objective scores remain bounded in [0.0, 1.0]."""

    staleness_window: timedelta = timedelta(days=365)
    currency_floor: float = 0.3
    target_policy_rule_count: int = 1
    empty_chain_score: float = 0.5
    severity_weights: Mapping[ExceptionSeverity, float] = field(
        default_factory=lambda: dict(_DEFAULT_SEVERITY_WEIGHTS)
    )
    overdue_penalty: float = 0.10
    # Optional scalar composite weights. None => vector-only (recommended).
    composite_weights: Mapping[str, float] | None = None


@dataclass(frozen=True)
class GovernanceFitnessInput:
    """The governance state to evaluate, expressed entirely as ISR.

    Sourcing contract:
      * ``exceptions`` MUST be the ACTIVE set (post-revocation), e.g. from
        ExceptionRegistry.active(now). Revocation state lives outside the ISR
        by design, so the caller supplies the filtered set.
      * ``evidence`` MUST be in chain order (as recorded).
    """

    versions: tuple[ConstitutionVersionISR, ...] = ()
    compliance_reports: tuple[ComplianceReportISR, ...] = ()
    exceptions: tuple[GovernanceExceptionISR, ...] = ()
    evidence: tuple[AuditEvidenceISR, ...] = ()
    lineage: tuple[ChangeLineageISR, ...] = ()
    policy_rules: tuple[PolicyRuleISR, ...] = ()


@dataclass(frozen=True)
class GovernanceFitnessResult:
    """Multi-objective governance fitness signal.

    ``objectives`` is the primary output (a bounded vector, never collapsed).
    ``composite`` is an optional, opt-in scalar for convenience only.
    """

    objectives: Mapping[str, float]
    details: Mapping[str, str]
    evaluated_at: datetime
    composite: float | None = None


class GovernanceFitnessDimension:
    """Evaluates governance health as a bounded multi-objective fitness signal.

    Pure and deterministic for a given (input, now, config).

    Not deprecated: this measures the platform's OWN constitutional health
    (a candidate telemetry input to the continuous-evolution loop), distinct
    from per-candidate selection fitness -- see
    ``evolution/governance_fitness_evaluator.py``.
    """

    def __init__(self, config: GovernanceFitnessConfig | None = None) -> None:
        self._config = config or GovernanceFitnessConfig()

    def evaluate(
        self, state: GovernanceFitnessInput, now: datetime
    ) -> GovernanceFitnessResult:
        objectives: dict[str, float] = {}
        details: dict[str, str] = {}

        score, why = self._constitutional_currency(state.versions, now)
        objectives[OBJECTIVE_CONSTITUTIONAL_CURRENCY] = score
        details[OBJECTIVE_CONSTITUTIONAL_CURRENCY] = why

        score, why = self._compliance_posture(state.compliance_reports)
        objectives[OBJECTIVE_COMPLIANCE_POSTURE] = score
        details[OBJECTIVE_COMPLIANCE_POSTURE] = why

        score, why = self._exception_hygiene(state.exceptions, now)
        objectives[OBJECTIVE_EXCEPTION_HYGIENE] = score
        details[OBJECTIVE_EXCEPTION_HYGIENE] = why

        score, why = self._audit_integrity(state.evidence)
        objectives[OBJECTIVE_AUDIT_INTEGRITY] = score
        details[OBJECTIVE_AUDIT_INTEGRITY] = why

        score, why = self._ratification_rigor(state.versions)
        objectives[OBJECTIVE_RATIFICATION_RIGOR] = score
        details[OBJECTIVE_RATIFICATION_RIGOR] = why

        score, why = self._policy_coverage(state.policy_rules)
        objectives[OBJECTIVE_POLICY_COVERAGE] = score
        details[OBJECTIVE_POLICY_COVERAGE] = why

        return GovernanceFitnessResult(
            objectives=objectives,
            details=details,
            evaluated_at=now,
            composite=self._composite(objectives),
        )

    # -- individual objectives --------------------------------------------

    def _constitutional_currency(
        self, versions: tuple[ConstitutionVersionISR, ...], now: datetime
    ) -> tuple[float, str]:
        ratified = [v for v in versions if v.status is VersionStatus.RATIFIED]
        if not ratified:
            return 0.0, "no_ratified_head"
        if len(ratified) > 1:
            # Invariant violation: at most one ratified head. Fail closed.
            return 0.0, f"invariant_violation_multiple_heads:{len(ratified)}"
        head = ratified[0]
        if head.effective_at is None:
            return self._config.currency_floor, "ratified_without_effective_at"
        age = now - head.effective_at
        window = self._config.staleness_window
        if age <= timedelta(0) or window <= timedelta(0):
            freshness = 1.0
        else:
            freshness = max(0.0, 1.0 - (age / window))
        floor = self._config.currency_floor
        score = floor + (1.0 - floor) * freshness
        return score, f"ratified_head_age={age}"

    def _compliance_posture(
        self, reports: tuple[ComplianceReportISR, ...]
    ) -> tuple[float, str]:
        if not reports:
            return 0.0, "no_compliance_reports"
        weight = {
            ComplianceOutcome.COMPLIANT: 1.0,
            ComplianceOutcome.INDETERMINATE: 0.5,
            ComplianceOutcome.NON_COMPLIANT: 0.0,
        }
        total = sum(weight[r.outcome] for r in reports)
        return total / len(reports), f"reports={len(reports)}"

    def _exception_hygiene(
        self, exceptions: tuple[GovernanceExceptionISR, ...], now: datetime
    ) -> tuple[float, str]:
        open_exceptions = [e for e in exceptions if self._is_open(e, now)]
        if not open_exceptions:
            return 1.0, "no_open_exceptions"
        penalty = 0.0
        overdue_count = 0
        for exc in open_exceptions:
            penalty += self._config.severity_weights.get(exc.severity, 0.0)
            if exc.review_due < now:
                penalty += self._config.overdue_penalty
                overdue_count += 1
        score = max(0.0, 1.0 - penalty)
        return score, f"open_exceptions={len(open_exceptions)}:overdue={overdue_count}"

    def _audit_integrity(
        self, evidence: tuple[AuditEvidenceISR, ...]
    ) -> tuple[float, str]:
        if not evidence:
            return self._config.empty_chain_score, "empty_evidence_chain"
        previous_id: str | None = None
        for record in evidence:
            if record.chain_link != previous_id:
                return 0.0, f"chain_break_at={record.evidence_id}"
            previous_id = record.evidence_id
        return 1.0, f"chain_intact_records={len(evidence)}"

    def _ratification_rigor(
        self, versions: tuple[ConstitutionVersionISR, ...]
    ) -> tuple[float, str]:
        ratified = [v for v in versions if v.status is VersionStatus.RATIFIED]
        if not ratified:
            return 0.0, "no_ratified_versions"
        authorized = [
            v for v in ratified if v.ratification_workflow_ref and v.lineage_ref
        ]
        return len(authorized) / len(ratified), (
            f"authorized={len(authorized)}/{len(ratified)}"
        )

    def _policy_coverage(
        self, rules: tuple[PolicyRuleISR, ...]
    ) -> tuple[float, str]:
        if not rules:
            return 0.0, "no_policy_rules"
        target = self._config.target_policy_rule_count
        if target <= 0:
            return 1.0, f"rules={len(rules)}:target_disabled"
        score = min(1.0, len(rules) / target)
        return score, f"rules={len(rules)}:target={target}"

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _is_open(exc: GovernanceExceptionISR, now: datetime) -> bool:
        return exc.expires_at is None or exc.expires_at > now

    def _composite(self, objectives: Mapping[str, float]) -> float | None:
        weights = self._config.composite_weights
        if not weights:
            return None
        acc = 0.0
        total_weight = 0.0
        for name in ALL_OBJECTIVES:
            w = weights.get(name, 0.0)
            if w > 0:
                acc += w * objectives.get(name, 0.0)
                total_weight += w
        if total_weight <= 0:
            return None
        return acc / total_weight


# ===========================================================================
# ADAPTER SEAM (framework-neutral result -> platform fitness engine)
# ===========================================================================
#
# The dimension above is deliberately decoupled from any fitness framework.
# To plug it into the evolution engine, a thin adapter:
#   1. Collects governance ISR into GovernanceFitnessInput (collector below).
#   2. Calls dimension.evaluate(state, now).
#   3. Maps GovernanceFitnessResult.objectives into the engine's fitness shape.
#
# ADAPTATION POINT (needs confirmation): the exact platform fitness interface
# (FitnessDimension / FitnessEvaluator signature) and how objectives feed the
# Pareto optimiser. Once confirmed, only this seam is finalised; the core is
# untouched.
# ===========================================================================


def collect_governance_state(
    *,
    versions,
    compliance_reports,
    exceptions_registry,
    evidence_recorder,
    lineage,
    policy_rules,
    now: datetime,
) -> GovernanceFitnessInput:
    """Build a GovernanceFitnessInput from the Phase 28 runtime subsystems.

    Sourcing rules:
      * versions           <- VersionManager.history()
      * compliance_reports <- ComplianceReportLog.latest(...)
      * exceptions         <- ExceptionRegistry.active(now)  # post-revocation
      * evidence           <- AuditEvidenceRecorder.entries   # chain order
      * lineage            <- VersionManager.lineage()
      * policy_rules       <- normalized PolicyRuleISR set from
                              normalize_policy_set(policy_set)
    """
    return GovernanceFitnessInput(
        versions=tuple(versions),
        compliance_reports=tuple(compliance_reports),
        exceptions=tuple(exceptions_registry.active(now)),
        evidence=tuple(evidence_recorder.entries),
        lineage=tuple(lineage),
        policy_rules=tuple(policy_rules),
    )


def to_fitness_objectives(result: GovernanceFitnessResult) -> dict[str, float]:
    """Expose the multi-objective signal as a plain objective map, the common
    shape consumed by Pareto-based fitness engines. Objectives stay separate
    (never collapsed) so the optimiser sees the full vector."""
    return dict(result.objectives)
