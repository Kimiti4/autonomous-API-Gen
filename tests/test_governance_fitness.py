"""Option (d) - Governance Fitness Dimension: bounded multi-objective evaluation
of the constitutional governance state (the selection half of the governance
evolutionary loop)."""

from datetime import datetime, timedelta, timezone

import pytest

from constitutional_architecture.governance.governance_fitness import (
    ALL_OBJECTIVES,
    GovernanceFitnessConfig,
    GovernanceFitnessDimension,
    GovernanceFitnessInput,
    GovernanceFitnessResult,
    collect_governance_state,
    to_fitness_objectives,
)
from constitutional_architecture.governance.schemas import (
    AuditEvidenceISR,
    ComplianceOutcome,
    ComplianceReportISR,
    ConstitutionVersionISR,
    ExceptionSeverity,
    GovernanceExceptionISR,
    PolicyRuleISR,
    VersionStatus,
)

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)


def make_version(
    semver="1.0.0",
    version_id=None,
    status=VersionStatus.RATIFIED,
    effective_at=None,
    workflow_ref="wf-1",
    lineage_ref="lineage-1",
):
    return ConstitutionVersionISR(
        version_id=version_id or f"v-{semver}",
        semver=semver,
        status=status,
        policy_set_ref="ps-1",
        proposed_by="architect",
        proposed_at=NOW - timedelta(days=400),
        predecessor_ref=None,
        ratification_workflow_ref=workflow_ref,
        lineage_ref=lineage_ref,
        effective_at=effective_at,
    )


def make_exception(
    severity=ExceptionSeverity.LOW,
    granted_at=None,
    review_due=None,
    expires_at=None,
    exception_id="exc-1",
):
    granted_at = granted_at or NOW - timedelta(days=10)
    review_due = review_due or NOW + timedelta(days=30)
    return GovernanceExceptionISR(
        exception_id=exception_id,
        scope="subject|action|resource",
        severity=severity,
        justification="j",
        granted_by="approver",
        granted_at=granted_at,
        review_due=review_due,
        expires_at=expires_at,
    )


def make_report(outcome=ComplianceOutcome.COMPLIANT, ref="r-1"):
    return ComplianceReportISR(
        report_id=ref,
        policy_set_ref="ps-1",
        subject="s",
        evaluated_at=NOW,
        outcome=outcome,
        violations=[],
        evidence_refs=[],
    )


def make_evidence(eid="e-1", chain_link=None):
    return AuditEvidenceISR(
        evidence_id=eid,
        recorded_at=NOW,
        actor="actor",
        event_kind="ratification",
        subject_ref="v-1",
        payload_hash="00",
        chain_link=chain_link,
    )


def make_rule(rule_id="r-1"):
    return PolicyRuleISR(
        rule_id=rule_id,
        subject="*",
        action="*",
        resource="*",
    )


def build_input(**kwargs) -> GovernanceFitnessInput:
    defaults = dict(
        versions=(),
        compliance_reports=(),
        exceptions=(),
        evidence=(),
        lineage=(),
        policy_rules=(),
    )
    defaults.update(kwargs)
    return GovernanceFitnessInput(**defaults)


def evaluate(**kwargs) -> GovernanceFitnessResult:
    return GovernanceFitnessDimension().evaluate(build_input(**kwargs), NOW)


def test_all_objectives_present_and_stable():
    assert ALL_OBJECTIVES == (
        "constitutional_currency",
        "compliance_posture",
        "exception_hygiene",
        "audit_integrity",
        "ratification_rigor",
        "policy_coverage",
    )


def test_empty_state_all_objectives_bounded():
    res = evaluate()
    for key in ALL_OBJECTIVES:
        assert key in res.objectives
        assert 0.0 <= res.objectives[key] <= 1.0


def test_empty_state_is_fail_closed():
    res = evaluate()
    assert res.objectives["constitutional_currency"] == 0.0
    assert res.objectives["compliance_posture"] == 0.0
    assert res.objectives["policy_coverage"] == 0.0
    assert res.objectives["ratification_rigor"] == 0.0
    assert res.objectives["exception_hygiene"] == 1.0
    assert 0.0 < res.objectives["audit_integrity"] <= 1.0


def test_constitutional_currency_no_ratified_head():
    v = make_version(status=VersionStatus.PROPOSED, effective_at=None)
    res = evaluate(versions=(v,))
    assert res.objectives["constitutional_currency"] == 0.0
    assert "no_ratified_head" in res.details["constitutional_currency"]


def test_constitutional_currency_ratified_without_effective_at_uses_floor():
    v = make_version(effective_at=None)
    res = evaluate(versions=(v,))
    cfg = GovernanceFitnessConfig()
    assert res.objectives["constitutional_currency"] == cfg.currency_floor
    assert "ratified_without_effective_at" in res.details["constitutional_currency"]


def test_constitutional_currency_fresh_head_is_full_score():
    v = make_version(effective_at=NOW)
    res = evaluate(versions=(v,))
    assert res.objectives["constitutional_currency"] == 1.0


def test_constitutional_currency_stale_head_decays_to_floor():
    window = GovernanceFitnessConfig().staleness_window
    v = make_version(effective_at=NOW - window - timedelta(days=1))
    res = evaluate(versions=(v,))
    cfg = GovernanceFitnessConfig()
    assert res.objectives["constitutional_currency"] == cfg.currency_floor


def test_constitutional_currency_multiple_ratified_heads_is_fail_closed():
    v1 = make_version(semver="1.0.0", effective_at=NOW)
    v2 = make_version(semver="1.1.0", effective_at=NOW, version_id="v-1.1.0")
    res = evaluate(versions=(v1, v2))
    assert res.objectives["constitutional_currency"] == 0.0
    assert "invariant_violation" in res.details["constitutional_currency"]


def test_compliance_posture_no_reports():
    res = evaluate(compliance_reports=())
    assert res.objectives["compliance_posture"] == 0.0
    assert "no_compliance_reports" in res.details["compliance_posture"]


def test_compliance_posture_all_compliant():
    res = evaluate(
        compliance_reports=(
            make_report(ComplianceOutcome.COMPLIANT),
            make_report(ComplianceOutcome.COMPLIANT),
        )
    )
    assert res.objectives["compliance_posture"] == 1.0


def test_compliance_posture_mixed_weighted_average():
    reports = (
        make_report(ComplianceOutcome.COMPLIANT, ref="r-1"),
        make_report(ComplianceOutcome.INDETERMINATE, ref="r-2"),
        make_report(ComplianceOutcome.NON_COMPLIANT, ref="r-3"),
    )
    res = evaluate(compliance_reports=reports)
    expected = (1.0 + 0.5 + 0.0) / 3
    assert res.objectives["compliance_posture"] == pytest.approx(expected)


def test_compliance_posture_all_non_compliant():
    res = evaluate(compliance_reports=(make_report(ComplianceOutcome.NON_COMPLIANT),))
    assert res.objectives["compliance_posture"] == 0.0


def test_exception_hygiene_no_open_exceptions():
    res = evaluate(exceptions=())
    assert res.objectives["exception_hygiene"] == 1.0
    assert "no_open_exceptions" in res.details["exception_hygiene"]


def test_exception_hygiene_critical_exception_penalty():
    exc = make_exception(severity=ExceptionSeverity.CRITICAL)
    res = evaluate(exceptions=(exc,))
    cfg = GovernanceFitnessConfig()
    penalty = cfg.severity_weights[ExceptionSeverity.CRITICAL]
    expected = max(0.0, 1.0 - penalty)
    assert res.objectives["exception_hygiene"] == pytest.approx(expected)


def test_exception_hygiene_overdue_extra_penalty():
    exc = make_exception(
        severity=ExceptionSeverity.LOW,
        review_due=NOW - timedelta(days=1),
    )
    res = evaluate(exceptions=(exc,))
    cfg = GovernanceFitnessConfig()
    penalty = cfg.severity_weights[ExceptionSeverity.LOW] + cfg.overdue_penalty
    expected = max(0.0, 1.0 - penalty)
    assert res.objectives["exception_hygiene"] == pytest.approx(expected)


def test_exception_hygiene_expired_exception_is_closed():
    exc = make_exception(
        severity=ExceptionSeverity.CRITICAL,
        expires_at=NOW - timedelta(days=1),
    )
    res = evaluate(exceptions=(exc,))
    assert res.objectives["exception_hygiene"] == 1.0


def test_audit_integrity_empty_chain_uses_empty_chain_score():
    res = evaluate(evidence=())
    cfg = GovernanceFitnessConfig()
    assert res.objectives["audit_integrity"] == cfg.empty_chain_score
    assert "empty_evidence_chain" in res.details["audit_integrity"]


def test_audit_integrity_intact_chain_is_full_score():
    e1 = make_evidence(eid="e-1", chain_link=None)
    e2 = make_evidence(eid="e-2", chain_link="e-1")
    e3 = make_evidence(eid="e-3", chain_link="e-2")
    res = evaluate(evidence=(e1, e2, e3))
    assert res.objectives["audit_integrity"] == 1.0
    assert "chain_intact" in res.details["audit_integrity"]


def test_audit_integrity_broken_chain_is_zero():
    e1 = make_evidence(eid="e-1", chain_link=None)
    e2 = make_evidence(eid="e-2", chain_link="WRONG")
    res = evaluate(evidence=(e1, e2))
    assert res.objectives["audit_integrity"] == 0.0
    assert "chain_break" in res.details["audit_integrity"]


def test_ratification_rigor_no_ratified():
    v = make_version(status=VersionStatus.PROPOSED)
    res = evaluate(versions=(v,))
    assert res.objectives["ratification_rigor"] == 0.0
    assert "no_ratified_versions" in res.details["ratification_rigor"]


def test_ratification_rigor_authorized_ratio():
    authorized = make_version(workflow_ref="wf-1", lineage_ref="l-1")
    missing_workflow = make_version(
        semver="2.0.0",
        version_id="v-2.0.0",
        workflow_ref=None,
        lineage_ref="l-2",
    )
    res = evaluate(versions=(authorized, missing_workflow))
    assert res.objectives["ratification_rigor"] == pytest.approx(0.5)
    assert "authorized=1/2" in res.details["ratification_rigor"]


def test_policy_coverage_no_rules():
    res = evaluate(policy_rules=())
    assert res.objectives["policy_coverage"] == 0.0
    assert "no_policy_rules" in res.details["policy_coverage"]


def test_policy_coverage_meets_target_is_full_score():
    res = evaluate(policy_rules=(make_rule(),))
    assert res.objectives["policy_coverage"] == 1.0
    assert "rules=1" in res.details["policy_coverage"]


def test_policy_coverage_capped_at_target():
    cfg = GovernanceFitnessConfig(target_policy_rule_count=1)
    rules = tuple(make_rule(rule_id=f"r-{i}") for i in range(5))
    res = GovernanceFitnessDimension(cfg).evaluate(build_input(policy_rules=rules), NOW)
    assert res.objectives["policy_coverage"] == 1.0


def test_policy_coverage_scales_below_target():
    cfg = GovernanceFitnessConfig(target_policy_rule_count=4)
    res = GovernanceFitnessDimension(cfg).evaluate(
        build_input(policy_rules=(make_rule(),)), NOW
    )
    assert res.objectives["policy_coverage"] == pytest.approx(1 / 4)


def test_default_config_composite_is_none_vector_only():
    res = evaluate()
    assert res.composite is None


def test_composite_with_weights_is_weighted_average():
    weights = {
        "constitutional_currency": 0.5,
        "compliance_posture": 0.5,
        "exception_hygiene": 0.0,
        "audit_integrity": 0.0,
        "ratification_rigor": 0.0,
        "policy_coverage": 0.0,
    }
    cfg = GovernanceFitnessConfig(composite_weights=weights)
    v = make_version(effective_at=NOW)
    res = GovernanceFitnessDimension(cfg).evaluate(
        build_input(versions=(v,), compliance_reports=(make_report(),)), NOW
    )
    expected = 0.5 * 1.0 + 0.5 * 1.0
    assert res.composite == pytest.approx(expected)


def test_composite_no_positive_weights_is_none():
    cfg = GovernanceFitnessConfig(composite_weights={obj: 0.0 for obj in ALL_OBJECTIVES})
    res = GovernanceFitnessDimension(cfg).evaluate(build_input(), NOW)
    assert res.composite is None


def test_all_results_bounded_in_unit_interval():
    v = make_version(effective_at=NOW)
    reports = (make_report(ComplianceOutcome.COMPLIANT),)
    rules = (make_rule(), make_rule(rule_id="r-2"))
    evidence = (
        make_evidence(eid="e-1", chain_link=None),
        make_evidence(eid="e-2", chain_link="e-1"),
    )
    res = evaluate(
        versions=(v,),
        compliance_reports=reports,
        exceptions=(make_exception(),),
        evidence=evidence,
        policy_rules=rules,
    )
    for key in ALL_OBJECTIVES:
        assert 0.0 <= res.objectives[key] <= 1.0


def test_evaluation_is_deterministic():
    v = make_version(effective_at=NOW)
    inp = build_input(versions=(v,), policy_rules=(make_rule(),))
    dim = GovernanceFitnessDimension()
    first = dim.evaluate(inp, NOW)
    second = dim.evaluate(inp, NOW)
    assert first.objectives == second.objectives
    assert first.details == second.details


def test_evaluated_at_carries_through_now():
    res = evaluate()
    assert res.evaluated_at == NOW


def test_custom_config_overrides_apply():
    cfg = GovernanceFitnessConfig(currency_floor=0.1, empty_chain_score=0.25)
    v = make_version(effective_at=None)
    res = GovernanceFitnessDimension(cfg).evaluate(
        build_input(versions=(v,), evidence=()), NOW
    )
    assert res.objectives["constitutional_currency"] == 0.1
    assert res.objectives["audit_integrity"] == 0.25


def test_to_fitness_objectives_returns_plain_dict_copy():
    res = evaluate()
    obj = to_fitness_objectives(res)
    assert isinstance(obj, dict)
    assert obj == dict(res.objectives)
    obj["mutated"] = 999.0
    assert "mutated" not in res.objectives


class _StubRegistry:
    def __init__(self, all_exceptions):
        self._all = all_exceptions

    def active(self, now):
        return tuple(
            e for e in self._all if e.expires_at is None or e.expires_at > now
        )


class _StubRecorder:
    def __init__(self, entries):
        self.entries = entries


def test_collect_governance_state_filters_active_exceptions():
    expired = make_exception(expires_at=NOW - timedelta(days=1))
    active = make_exception(expires_at=None, exception_id="exc-2")
    registry = _StubRegistry(all_exceptions=(expired, active))
    recorder = _StubRecorder(entries=())
    inp = collect_governance_state(
        versions=(),
        compliance_reports=(),
        exceptions_registry=registry,
        evidence_recorder=recorder,
        lineage=(),
        policy_rules=(),
        now=NOW,
    )
    ids = {e.exception_id for e in inp.exceptions}
    assert "exc-2" in ids
    assert expired.exception_id not in ids
    assert len(inp.exceptions) == 1


def test_collect_governance_state_preserves_chain_order():
    e1 = make_evidence(eid="e-1", chain_link=None)
    e2 = make_evidence(eid="e-2", chain_link="e-1")
    recorder = _StubRecorder(entries=(e1, e2))
    inp = collect_governance_state(
        versions=(),
        compliance_reports=(),
        exceptions_registry=_StubRegistry(all_exceptions=()),
        evidence_recorder=recorder,
        lineage=(),
        policy_rules=(),
        now=NOW,
    )
    assert tuple(e.evidence_id for e in inp.evidence) == ("e-1", "e-2")
