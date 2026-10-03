from app.engine.evidence_fitness import *

def obs():
    return {
        "correctness":.95,"correctness_evidence":["workflow-1"],
        "security":.9,"security_evidence":["security-1"],
        "performance":.8,"performance_evidence":["perf-1"],
        "resilience":.85,"resilience_evidence":["chaos-1"],
        "accessibility":.9,"accessibility_evidence":["a11y-1"],
        "maintainability":.8,"maintainability_evidence":["static-1"],
    }

def test_metrics_are_evidence_derived():
    f=from_observations(obs())
    assert f.value("security")==.9
    assert "security-1" in f.evidence()

def test_missing_evidence_does_not_create_metric():
    o=obs()
    del o["security_evidence"]
    f=from_observations(o)
    assert "security" not in f.metrics

def test_metric_without_evidence_is_rejected():
    try:
        metric("security",.9,())
    except ValueError as e:
        assert str(e)=="metric-requires-evidence"
        return
    assert False

def test_out_of_range_is_rejected():
    try:
        metric("security",1.1,("e",))
    except ValueError:
        return
    assert False

def test_complete_fitness_requires_all_dimensions():
    f=from_observations(obs())
    require_complete_fitness(f)
    incomplete=from_observations({"security":.9,"security_evidence":["e"]})
    try:
        require_complete_fitness(incomplete)
    except ValueError as e:
        assert str(e).startswith("incomplete-evidence:")
        return
    assert False
