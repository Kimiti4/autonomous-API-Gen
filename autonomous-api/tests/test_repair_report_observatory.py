import pytest
from types import SimpleNamespace
from app.engine.repair_report_observatory import project_repair_report, serialize_observatory_repair_view

def report(**kw):
    base=dict(report_id="r",target="app",finding_ids=("f1",),verification=({"passed":True},),
      regressions=(),deployment_ready=False,human_deployment_authorization_required=True,
      residuals=(),selected_candidate_id="c",digest="d")
    base.update(kw)
    return SimpleNamespace(**base)

def test_report_projects_to_observable_validated_state():
    v=project_repair_report(report())
    assert v.status=="validated" and v.verification_passed and v.regression_free

def test_residuals_make_report_blocked():
    v=project_repair_report(report(residuals=("unknown",)))
    assert v.status=="blocked"

def test_invalid_ready_state_fails_closed():
    with pytest.raises(ValueError,match="invalid-deployment-ready-repair-report"):
        project_repair_report(report(deployment_ready=True,residuals=("x",)))

def test_serialization_is_deterministic():
    v=project_repair_report(report())
    assert serialize_observatory_repair_view(v)==serialize_observatory_repair_view(v)
