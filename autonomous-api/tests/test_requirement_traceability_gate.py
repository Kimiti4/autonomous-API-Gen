import pytest
from app.engine.requirement_traceability_gate import certify_traceability,require_traceability
from app.engine.implementation_traceability import ImplementationTrace,ImplementationTracePlan

def plan():
 return ImplementationTracePlan((ImplementationTrace("O1",("C1",),("impl:C1",),("V1",),("V1",),"planned"),),())
def test_complete_traceability():
 r=certify_traceability(("O1",),plan()); assert r.complete
def test_missing_trace_blocks():
 r=certify_traceability(("O1","O2"),plan()); assert not r.complete
 with pytest.raises(ValueError): require_traceability(r)
def test_missing_evidence_requirement_blocks():
 p=ImplementationTracePlan((ImplementationTrace("O1",("C1",),("impl:C1",),("V1",),(),"planned"),),())
 assert not certify_traceability(("O1",),p).complete
