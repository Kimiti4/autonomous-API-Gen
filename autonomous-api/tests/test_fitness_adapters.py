from app.engine.fitness_adapters import *

def test_workflow_report_derives_correctness():
    r=correctness_from_workflow({"property_results":[{"passed":True},{"passed":False}],"evidence":["w"]})
    assert r["correctness_score"]==.5
    assert r["correctness_evidence"]==("w",)

def test_security_report_derives_security_score():
    r=security_from_adversarial({"tests":[{"passed":True},{"passed":True},{"passed":False}],"evidence":["s"]})
    assert abs(r["security_score"]-2/3)<1e-9

def test_missing_performance_measurement_stays_unknown():
    assert performance_from_measurements({"evidence":["p"]})=={}

def test_all_dimension_reports_can_be_collected():
    f=collect_dimension_reports(
        {"property_results":[{"passed":True}],"evidence":["w"]},
        {"tests":[{"passed":True}],"evidence":["s"]},
        {"normalized_score":.8,"evidence":["p"]},
        {"normalized_score":.7,"evidence":["r"]},
        {"normalized_score":.9,"evidence":["a"]},
        {"normalized_score":.85,"evidence":["m"]},
    )
    assert set(f.metrics)=={"correctness","security","performance","resilience","accessibility","maintainability"}
    assert f.evidence()==("a","m","p","r","s","w")
