from app.engine.requirement_evidence_certification import certify_requirement_evidence
from app.engine.requirement_ir import Requirement,RequirementKind,RequirementPriority,AcceptanceCriterion,build_requirement_graph
from app.engine.implementation_traceability import ImplementationTracePlan,ImplementationTrace

def graph():
 return build_requirement_graph([Requirement("R-1","users sign in",RequirementKind.FUNCTIONAL,RequirementPriority.MUST,(AcceptanceCriterion("AC-1","ok"),),(),"test")])
def test_full_trace_certifies_requirement():
 p=ImplementationTracePlan((ImplementationTrace("AO-1",("auth",),("impl:auth",),("V-1",),("V-1",),"planned"),),())
 c=certify_requirement_evidence(graph(),{"AO-1":"R-1"},p,{"V-1":{"passed":True,"evidence_ids":("E-1",)}})
 assert c.certified and c.traces[0].evidence_ids==("E-1",)
def test_missing_evidence_fails_closed():
 p=ImplementationTracePlan((ImplementationTrace("AO-1",("auth",),("impl:auth",),("V-1",),("V-1",),"planned"),),())
 c=certify_requirement_evidence(graph(),{"AO-1":"R-1"},p,{"V-1":{"passed":True}})
 assert not c.certified and c.unresolved_requirement_ids==("R-1",)
