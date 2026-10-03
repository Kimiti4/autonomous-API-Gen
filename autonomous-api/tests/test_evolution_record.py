import pytest
from app.engine.evolution_record import *

def record(status="proposed"):
    return EvolutionRecord(
        "e1","arch-1","candidate-1","counter-1",
        ("evidence-1",),("risk-1",),("assumption-1",),
        ("invariant-1",),"authority-1",status)

def test_evolution_preserves_traceability():
    r=record()
    assert validate_evolution(r)==()
    assert r.trigger_counterexample_id=="counter-1"
    assert r.supporting_evidence_ids==("evidence-1",)

def test_authorized_evolution_requires_evidence():
    r=EvolutionRecord("e1","arch-1","c1",None,(),(),"",(),"auth","authorized")
    assert "authorized-evolution-requires-evidence" in validate_evolution(r)

def test_lineage_rejects_duplicate_evolution():
    l=EvolutionLineage((record(),))
    with pytest.raises(ValueError, match="duplicate-evolution-id"):
        append_evolution(l,record())

def test_lineage_can_retrieve_parent_architecture_history():
    l=EvolutionLineage((record(),EvolutionRecord(
        "e2","arch-2","candidate-2",None,("e2v",),(),(),(),"auth")))
    assert tuple(r.evolution_id for r in lineage_for_architecture(l,"arch-1"))==("e1",)

def test_invalid_status_is_rejected():
    assert "invalid-status" in validate_evolution(
        EvolutionRecord("e","a","c",None,(),(),(),(),"auth","unknown"))
