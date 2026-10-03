from app.engine.invariant_conflicts import *
from app.engine.invariant_contracts import Invariant

def inv(i,d,e):
    return Invariant(i,d,"property",(e,))

def test_conflict_detected_with_provenance():
    c=detect_conflict("c1",inv("A","frontend","e1"),inv("B","backend","e2"),"tradeoff")
    assert c.invariant_ids==("A","B")
    assert c.domains==("backend","frontend")
    assert c.evidence==("e1","e2")

def test_self_conflict_rejected():
    a=inv("A","frontend","e")
    try:
        detect_conflict("c",a,a,"x")
    except ValueError as e:
        assert str(e)=="cannot-conflict-with-self"
        return
    assert False

def test_resolution_must_address_both_sides():
    c=detect_conflict("c1",inv("A","frontend","e1"),inv("B","backend","e2"),"tradeoff")
    r=resolve_conflict(c,"r1",("A",),(),"adapt","r-e")
    try:
        require_conflict_resolution(c,r)
    except ValueError as e:
        assert str(e)=="unresolved-invariant-conflict"
        return
    assert False

def test_resolution_can_keep_one_and_retire_another():
    c=detect_conflict("c1",inv("A","frontend","e1"),inv("B","backend","e2"),"tradeoff")
    r=resolve_conflict(c,"r1",("A",),("B",),"B replaced by compatible architecture",("r-e",))
    require_conflict_resolution(c,r)

def test_same_invariant_cannot_be_both_kept_and_retired():
    c=detect_conflict("c1",inv("A","frontend","e1"),inv("B","backend","e2"),"tradeoff")
    try:
        resolve_conflict(c,"r1",("A",),("A",),"x",("e",))
    except ValueError as e:
        assert str(e)=="invariant-cannot-be-both-compatible-and-retired"
        return
    assert False
