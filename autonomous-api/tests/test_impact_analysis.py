from app.engine.impact_analysis import *

def r(kind,id): return ArtifactRef(kind,id)

def test_api_contract_change_reaches_frontend_and_tests():
    changed=(r("api","wallet-v2"),)
    edges=(
        ArtifactEdge(r("api","wallet-v2"),r("frontend","wallet-client"),"api-contract"),
        ArtifactEdge(r("api","wallet-v2"),r("tests","wallet-e2e"),"api-contract"),
    )
    report=analyze_impact(changed,edges)
    assert len(report.impacts)==2
    assert r("frontend","wallet-client") in report.unresolved

def test_data_contract_change_requires_data_and_verification_review():
    impact=Impact(r("schema","ledger-v2"),r("service","ledger"),"data-contract","changed")
    assert required_review_domains(impact)==("backend","migrations","analytics","verification")

def test_security_boundary_expands_review():
    impact=Impact(r("auth","effect-policy"),r("service","wallet"),"security-boundary","changed")
    assert "security" in required_review_domains(impact)
    assert "verification" in required_review_domains(impact)

def test_unknown_relations_still_require_verification():
    impact=Impact(r("x","a"),r("y","b"),"unknown","changed")
    assert required_review_domains(impact)==("verification",)
