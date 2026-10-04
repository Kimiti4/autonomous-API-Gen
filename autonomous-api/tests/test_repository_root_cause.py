from app.engine.repository_code_scan import scan_repository
from app.engine.repository_impact_analysis import analyze_finding_impact
from app.engine.repository_root_cause import derive_root_causes, generate_repair_candidates

def test_root_cause_is_evidence_backed():
    finding=scan_repository([("a.py","try:\n x()\nexcept:\n pass")]).findings[0]
    impact=analyze_finding_impact(finding.finding_id,"a.py",(("a.py","try:\n x()\nexcept:\n pass"),))
    hs=derive_root_causes(finding,impact)
    assert hs and impact.digest in hs[0].evidence

def test_competing_candidates_are_bounded_to_impact():
    finding=scan_repository([("a.py","try:\n x()\nexcept:\n pass")]).findings[0]
    impact=analyze_finding_impact(finding.finding_id,"a.py",(("a.py","try:\n x()\nexcept:\n pass"),))
    hs=derive_root_causes(finding,impact)
    cs=generate_repair_candidates(finding,impact,hs)
    assert len(cs)>=2
    assert all(c.required_verification_paths==("a.py",) for c in cs)
