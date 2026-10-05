"""Tests for Bucket 3 final integration."""

from types import SimpleNamespace

from app.engine.bucket3_integration import Bucket3IntegrationEngine


def state(complete=False):
    return SimpleNamespace(complete=complete)


def decision(executable=True, classification="required"):
    return SimpleNamespace(executable=executable, classification=classification)


def impact(bounded=True):
    return SimpleNamespace(bounded=bounded)


def consistency(ok=True):
    return SimpleNamespace(consistent=ok)


def nfr(admissible=True):
    return SimpleNamespace(admissible=admissible)


def test_all_governance_gates_admit_unfinished_work():
    result = Bucket3IntegrationEngine(project_id="p").evaluate_change(
        scope_decision=decision(),
        impact_plan=impact(),
        consistency_report=consistency(),
        nfr_assessment=nfr(),
        completion_state=state(False),
    )
    assert result.decision == "ADMIT"
    assert result.executable
    assert result.reasons == ()


def test_scope_failure_rejects_even_when_other_gates_pass():
    result = Bucket3IntegrationEngine(project_id="p").evaluate_change(
        scope_decision=decision(False, "advisory"),
        impact_plan=impact(),
        consistency_report=consistency(),
        nfr_assessment=nfr(),
        completion_state=state(False),
    )
    assert result.decision == "REJECT"
    assert "scope-not-executable" in result.reasons


def test_unbounded_impact_rejects():
    result = Bucket3IntegrationEngine(project_id="p").evaluate_change(
        scope_decision=decision(),
        impact_plan=impact(False),
        consistency_report=consistency(),
        nfr_assessment=nfr(),
        completion_state=state(False),
    )
    assert result.decision == "REJECT"
    assert "mutation-impact-unbounded" in result.reasons


def test_consistency_or_nfr_failure_rejects():
    result = Bucket3IntegrationEngine(project_id="p").evaluate_change(
        scope_decision=decision(),
        impact_plan=impact(),
        consistency_report=consistency(False),
        nfr_assessment=nfr(False),
        completion_state=state(False),
    )
    assert result.decision == "REJECT"
    assert set(result.reasons) == {
        "cross-layer-inconsistency",
        "nfr-admission-failed",
    }


def test_completed_project_is_a_stop_boundary():
    result = Bucket3IntegrationEngine(project_id="p").evaluate_change(
        scope_decision=decision(),
        impact_plan=impact(),
        consistency_report=consistency(),
        nfr_assessment=nfr(),
        completion_state=state(True),
    )
    assert result.decision == "STOP"
    assert not result.executable
    assert "project-already-complete" in result.reasons


def test_completion_evaluation_stops_only_when_complete():
    engine = Bucket3IntegrationEngine(project_id="p")
    assert engine.evaluate_completion(state(True)).decision == "STOP"
    assert engine.evaluate_completion(state(False)).decision == "REJECT"


def test_digest_is_deterministic():
    engine = Bucket3IntegrationEngine(project_id="p")
    args = dict(
        scope_decision=decision(),
        impact_plan=impact(),
        consistency_report=consistency(),
        nfr_assessment=nfr(),
        completion_state=state(False),
    )
    assert engine.evaluate_change(**args).digest == engine.evaluate_change(**args).digest
