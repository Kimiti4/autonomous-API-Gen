from app.engine.repository_impact_analysis import analyze_finding_impact

def test_finding_impact_finds_direct_and_transitive_dependents():
    files=[
      ("core.py","x=1"),
      ("service.py","from core import x"),
      ("api.py","from service import x"),
    ]
    r=analyze_finding_impact("f1","core.py",files)
    assert [(x.path,x.distance) for x in r.affected]==[("service.py",1),("api.py",2)]

def test_impact_analysis_is_deterministic():
    files=[("b.py","from a import x"),("a.py","x=1")]
    assert analyze_finding_impact("f","a.py",files).digest==analyze_finding_impact("f","a.py",tuple(reversed(files))).digest
