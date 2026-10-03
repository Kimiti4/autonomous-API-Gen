from app.engine.tradeoff_experiments import *

def alt():
    return create_alternative("a1","c1","hybrid",
        ("versioned-sync",),("CONSISTENCY",),("LATENCY",))

def test_alternative_requires_change():
    try:
        create_alternative("a","c","x",(),("p",),())
    except ValueError as e:
        assert str(e)=="tradeoff-requires-changes"
        return
    assert False

def test_observation_requires_measurements_and_evidence():
    try:
        observe(alt(),{},("e",))
    except ValueError as e:
        assert str(e)=="tradeoff-requires-measurements"
        return
    assert False

def test_tradeoff_assessment_preserves_measured_provenance():
    o=observe(alt(),{"latency_ms":120,"consistent":True},("trace-1",))
    a=assess(alt(),o)
    assert a.status=="bounded"
    assert a.measurements["latency_ms"]==120
    assert a.evidence==("trace-1",)

def test_observation_cannot_be_assigned_to_other_alternative():
    other=create_alternative("a2","c1","other",("change",),("P",),())
    o=observe(alt(),{"x":1},("e",))
    try:
        assess(other,o)
    except ValueError as e:
        assert str(e)=="tradeoff-alternative-mismatch"
        return
    assert False
