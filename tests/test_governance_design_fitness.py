"""Governance Design Fitness — bounded scoring, objective-vocabulary
consistency with option (d), and gene->dimension causality."""

from datetime import datetime, timezone

from constitutional_architecture.governance.governance_design_fitness import (
    GovernanceDesignFitness,
    design_objectives,
)
from constitutional_architecture.governance.governance_fitness import (
    ALL_OBJECTIVES,
    OBJECTIVE_AUDIT_INTEGRITY,
    OBJECTIVE_COMPLIANCE_POSTURE,
    OBJECTIVE_CONSTITUTIONAL_CURRENCY,
    OBJECTIVE_EXCEPTION_HYGIENE,
    OBJECTIVE_POLICY_COVERAGE,
    OBJECTIVE_RATIFICATION_RIGOR,
)
from constitutional_architecture.governance.schemas import (
    ExceptionSeverity,
    GovernanceDesignISR,
    VersioningStrategyKind,
    VotingRuleKind,
)

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def make_design(**overrides) -> GovernanceDesignISR:
    base = dict(
        design_id="gd-test",
        voting_rule=VotingRuleKind.SIMPLE_MAJORITY,
        quorum=1,
        approval_stage_count=1,
        policy_rule_count=0,
        fail_closed_default=False,
        exception_max_severity=ExceptionSeverity.CRITICAL,
        exception_review_required=False,
        audit_chaining_required=False,
        compliance_evaluation_required=False,
        versioning_strategy=VersioningStrategyKind.MONOTONIC_COUNTER,
    )
    base.update(overrides)
    return GovernanceDesignISR(**base)


STRICT = make_design(
    voting_rule=VotingRuleKind.UNANIMITY,
    quorum=5,
    approval_stage_count=3,
    policy_rule_count=10,
    fail_closed_default=True,
    exception_max_severity=ExceptionSeverity.LOW,
    exception_review_required=True,
    audit_chaining_required=True,
    compliance_evaluation_required=True,
    versioning_strategy=VersioningStrategyKind.SEMVER_CHAIN,
)
LAX = make_design()


def evaluate(design):
    return GovernanceDesignFitness().evaluate(design, NOW)


def test_scores_bounded_and_full_objective_set():
    result = evaluate(STRICT)
    assert set(result.objectives) == set(ALL_OBJECTIVES)
    assert all(0.0 <= value <= 1.0 for value in result.objectives.values())


def test_objective_names_match_operational_dimension():
    """Dimension-set consistency: design scoring emits the same six keys the
    option-(d) operational dimension and the bridge expect."""
    assert set(evaluate(STRICT).objectives) == set(ALL_OBJECTIVES)


def test_strict_design_dominates_lax_design():
    strict, lax = evaluate(STRICT).objectives, evaluate(LAX).objectives
    for name in ALL_OBJECTIVES:
        assert strict[name] > lax[name], name


def test_unanimity_more_rigorous_than_simple_majority():
    strict = evaluate(make_design(voting_rule=VotingRuleKind.UNANIMITY))
    lax = evaluate(make_design(voting_rule=VotingRuleKind.SIMPLE_MAJORITY))
    assert (
        strict.objectives[OBJECTIVE_RATIFICATION_RIGOR]
        > lax.objectives[OBJECTIVE_RATIFICATION_RIGOR]
    )


def test_higher_quorum_not_less_rigorous():
    low = evaluate(make_design(quorum=1))
    high = evaluate(make_design(quorum=5))
    assert (
        high.objectives[OBJECTIVE_RATIFICATION_RIGOR]
        >= low.objectives[OBJECTIVE_RATIFICATION_RIGOR]
    )


def test_fail_closed_higher_policy_coverage():
    permissive = evaluate(
        make_design(policy_rule_count=5, fail_closed_default=False)
    )
    closed = evaluate(make_design(policy_rule_count=5, fail_closed_default=True))
    assert (
        closed.objectives[OBJECTIVE_POLICY_COVERAGE]
        > permissive.objectives[OBJECTIVE_POLICY_COVERAGE]
    )


def test_lower_exception_tolerance_higher_hygiene():
    tolerant = evaluate(
        make_design(exception_max_severity=ExceptionSeverity.CRITICAL)
    )
    strict = evaluate(make_design(exception_max_severity=ExceptionSeverity.LOW))
    assert (
        strict.objectives[OBJECTIVE_EXCEPTION_HYGIENE]
        > tolerant.objectives[OBJECTIVE_EXCEPTION_HYGIENE]
    )


def test_audit_mandate_higher_integrity():
    off = evaluate(make_design(audit_chaining_required=False))
    on = evaluate(make_design(audit_chaining_required=True))
    assert (
        on.objectives[OBJECTIVE_AUDIT_INTEGRITY]
        > off.objectives[OBJECTIVE_AUDIT_INTEGRITY]
    )


def test_compliance_mandate_higher_posture():
    off = evaluate(make_design(compliance_evaluation_required=False))
    on = evaluate(make_design(compliance_evaluation_required=True))
    assert (
        on.objectives[OBJECTIVE_COMPLIANCE_POSTURE]
        > off.objectives[OBJECTIVE_COMPLIANCE_POSTURE]
    )


def test_semver_chain_highest_currency():
    semver = evaluate(
        make_design(versioning_strategy=VersioningStrategyKind.SEMVER_CHAIN)
    )
    counter = evaluate(
        make_design(versioning_strategy=VersioningStrategyKind.MONOTONIC_COUNTER)
    )
    assert (
        semver.objectives[OBJECTIVE_CONSTITUTIONAL_CURRENCY]
        > counter.objectives[OBJECTIVE_CONSTITUTIONAL_CURRENCY]
    )


def test_design_scoring_is_deterministic():
    a = evaluate(STRICT).objectives
    b = evaluate(STRICT).objectives
    assert dict(a) == dict(b)


def test_design_objectives_shape_matches_bridge():
    objectives = design_objectives(STRICT)
    assert isinstance(objectives, dict)
    assert set(objectives) == set(ALL_OBJECTIVES)
    assert all(0.0 <= value <= 1.0 for value in objectives.values())
