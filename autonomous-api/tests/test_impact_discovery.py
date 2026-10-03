from app.engine.impact_discovery import *

def test_discovers_affected_domains():
    request=ImpactRequest("frontend",("frontend.api",),("api-contract","auth"))
    relations=(
        ImpactRelation("frontend","backend","api-contract",("trace-1",)),
        ImpactRelation("frontend","security","auth",("trace-2",)),
        ImpactRelation("frontend","data","cache",("trace-3",)),
    )
    plan=discover_impact(request,relations)
    assert plan.affected_domains==("backend","security")
    assert len(plan.findings)==2

def test_unrelated_relation_is_ignored():
    request=ImpactRequest("frontend",("frontend.api",),("api-contract",))
    relations=(ImpactRelation("backend","data","api-contract",("e",)),)
    plan=discover_impact(request,relations)
    assert plan.affected_domains==()

def test_unevidenced_relation_is_not_used():
    request=ImpactRequest("frontend",("frontend.api",),("api-contract",))
    relations=(ImpactRelation("frontend","backend","api-contract",()),)
    plan=discover_impact(request,relations)
    assert plan.affected_domains==()

def test_invalid_request_rejected():
    try:
        discover_impact(ImpactRequest("",(),()),())
    except ValueError as e:
        assert str(e)=="impact-request-requires-domain-and-paths"
        return
    assert False
