import pytest
from app.engine.capability_repair_routing import route_capability_failures
from app.engine.verification_failure_repair import VerificationFailure
from app.engine.work_mode import WorkMode

def failure(kind):
    return VerificationFailure("v", kind, "failed", ("digest",))

def test_routes_seo_failure_to_seo_capability():
    r=route_capability_failures(WorkMode.SEO,(failure("crawlability"),))
    assert r.capability=="seo"
    assert r.failed_properties==("crawlability",)

def test_routes_refactor_failure_to_refactor_capability():
    r=route_capability_failures(WorkMode.REFACTOR,(failure("behavior-preservation"),))
    assert r.capability=="refactor"

def test_unrelated_failure_fails_closed():
    with pytest.raises(ValueError, match="no-capability-failure-to-route:seo"):
        route_capability_failures(WorkMode.SEO,(failure("unrelated"),))
