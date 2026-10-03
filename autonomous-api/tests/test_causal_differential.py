from app.engine.causal_differential import *

def run(before_failed, after_failed, resolved, evidence=("e2",), changes=()):
    return DifferentialRun("base","cand",changes,
        {"failed_properties":before_failed},
        {"failed_properties":after_failed,"resolved_properties":resolved,"evidence":evidence})

def test_resolution_without_regression_is_supported():
    r=run(("AUTHZ",),(),("AUTHZ",),changes=(GenomeChange("security.authorization_model","old","new"),))
    a=assess_differential("cx","AUTHZ",r)
    assert a.resolved
    assert a.causal_confidence=="supported"

def test_regression_blocks_causal_acceptance():
    r=run(("AUTHZ",),("PERF",),("AUTHZ",),changes=(GenomeChange("security.authorization_model","old","new"),))
    a=assess_differential("cx","AUTHZ",r)
    assert not a.resolved
    assert a.regressions==("PERF",)

def test_no_change_cannot_claim_causality():
    r=run(("AUTHZ",),(),("AUTHZ",),changes=())
    a=assess_differential("cx","AUTHZ",r)
    assert a.causal_confidence=="insufficient"

def test_generalization_requires_related_runs():
    r=run(("AUTHZ",),(),("AUTHZ",),changes=(GenomeChange("security.authorization_model","old","new"),))
    assert require_generalization((r,r),"AUTHZ")==("e2",)

def test_generalization_fails_if_related_case_still_fails():
    r=run(("AUTHZ",),("AUTHZ",),(),changes=(GenomeChange("security.authorization_model","old","new"),))
    try:
        require_generalization((r,),"AUTHZ")
    except ValueError as e:
        assert str(e)=="generalization-not-demonstrated"
        return
    assert False
