import pytest
from types import SimpleNamespace
from app.engine.repair_report_observatory import project_repair_report
from app.engine.repair_observatory_stream import build_repair_observatory_event, serialize_repair_observatory_event

def view():
    return project_repair_report(SimpleNamespace(
      report_id="r",target="app",finding_ids=("f",),verification=({"passed":True},),
      regressions=(),deployment_ready=False,human_deployment_authorization_required=True,
      residuals=(),selected_candidate_id="c",digest="d"))

def test_event_contains_report_state_and_digest():
    e=build_repair_observatory_event(view(),sequence=3)
    assert e.event_type=="repair-report" and e.payload["status"]=="validated"
    assert len(e.digest)==64

def test_event_digest_is_deterministic():
    a=build_repair_observatory_event(view(),sequence=1)
    b=build_repair_observatory_event(view(),sequence=1)
    assert a.digest==b.digest
    assert serialize_repair_observatory_event(a)==serialize_repair_observatory_event(b)

def test_negative_sequence_fails_closed():
    with pytest.raises(ValueError,match="invalid-observatory-sequence"):
        build_repair_observatory_event(view(),sequence=-1)
