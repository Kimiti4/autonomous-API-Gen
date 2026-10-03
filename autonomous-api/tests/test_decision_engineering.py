from app.engine.decision_engineering import (
    EngineeringAlternative, assess_alternative, propose_decision
)

def alt():
    return EngineeringAlternative(
        "a1","transactional service",
        satisfies=("idempotency","auditability"),
        tradeoffs=("higher coordination",),
        risks=("database contention",),
    )

def test_assessment_marks_missing_requirement_inconclusive():
    a=assess_alternative(alt(),("e1",),("idempotency",))
    assert a.status=="INCONCLUSIVE"
    assert a.unresolved_requirements==("auditability",)

def test_supported_alternative_can_be_proposed():
    a=assess_alternative(alt(),("e1","e2"),("idempotency","auditability"))
    d=propose_decision("D1",(a,),"a1",("both required properties are evidenced",))
    assert d.selected_alternative_id=="a1"
    assert d.authorization_required

def test_inconclusive_alternative_cannot_be_selected():
    a=assess_alternative(alt(),("e1",),("idempotency",))
    try:
        propose_decision("D1",(a,),"a1",("selection",))
        assert False
    except ValueError:
        pass
