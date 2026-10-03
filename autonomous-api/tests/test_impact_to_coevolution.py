from app.engine.impact_to_coevolution import *
from app.engine.impact_discovery import *

def impact():
    return discover_impact(
        ImpactRequest("frontend",("frontend.api",),("api-contract","auth")),
        (
            ImpactRelation("frontend","backend","api-contract",("api-trace",)),
            ImpactRelation("frontend","security","auth",("auth-trace",)),
        ),
    )

def test_builds_domain_plans():
    p=build_coevolution_plan(impact(),("frontend","backend","security"),True)
    assert [x.domain for x in p.domains]==["backend","security"]
    assert p.domains[0].required_properties[0]=="api-contract"
    assert p.impact_complete

def test_incomplete_dependency_graph_is_uncertain():
    p=build_coevolution_plan(impact(),("frontend","backend","security"),False)
    assert not p.impact_complete
    assert "dependency-graph-incomplete" in p.uncertainty_reasons

def test_unknown_domain_is_not_silently_accepted():
    i=ImpactPlan(
        "frontend",
        ("payments",),
        (ImpactFinding(
            "payments",
            "payment-dependency",
            (ImpactRelation("frontend","payments","payment",("trace",)),),
        ),),
    )
    p=build_coevolution_plan(i,("frontend","backend"),True)
    assert not p.impact_complete
    assert "unknown-domain:payments" in p.uncertainty_reasons

def test_complete_plan_rejects_uncertainty():
    p=build_coevolution_plan(impact(),("frontend","backend","security"),False)
    try:
        require_complete_plan(p)
    except ValueError as e:
        assert str(e)=="coevolution-impact-uncertain:dependency-graph-incomplete"
        return
    assert False
