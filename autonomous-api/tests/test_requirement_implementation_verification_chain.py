import pytest
from app.engine.requirement_ir import *
from app.engine.requirement_architecture_bridge import *
from app.engine.architecture_obligations import *
from app.engine.implementation_traceability import *
from app.engine.verification_obligations import *
from app.engine.requirement_implementation_verification_chain import *

def setup_chain(with_arch=True,with_impl=True,with_ver=True):
 g=RequirementGraph(); g.add(Requirement("R1","create account",RequirementKind.FUNCTIONAL,acceptance_criteria=(AcceptanceCriterion("AC1","exists"),))); g.validate()
 o=ArchitectureObligation("AO-R1","R1","functional","create",( "V1",))
 m=ObligationMapping("AO-R1",("account-service",),True,"mapped",("evidence",))
 i=ImplementationTrace("AO-R1",("account-service",),("impl:account-service",),("V1",) if with_ver else (),("evidence",),"planned")
 a=ArchitecturePlan((RequirementArchitectureLink("R1","AO-R1","satisfies"),),()) if with_arch else ArchitecturePlan((),("R1",))
 ip=ImplementationTracePlan((i,),()) if with_impl else ImplementationTracePlan((),("AO-R1",))
 v=(VerificationObligation("V1","functional","account-service","create","exists"),)
 return g,a,(o,),(m,),ip,v
def test_complete():
 g,a,o,m,i,v=setup_chain(); c=certify_requirement_to_verification_chain(g,a,o,m,i,v); assert c.complete and c.verification_ids==("V1",)
def test_missing_architecture_blocks():
 g,a,o,m,i,v=setup_chain(False); c=certify_requirement_to_verification_chain(g,a,o,m,i,v); assert not c.complete
def test_missing_implementation_blocks():
 g,a,o,m,i,v=setup_chain(True,False); c=certify_requirement_to_verification_chain(g,a,o,m,i,v); assert not c.complete
def test_missing_verification_blocks():
 g,a,o,m,i,v=setup_chain(True,True,False); c=certify_requirement_to_verification_chain(g,a,o,m,i,v); assert not c.complete
def test_invalid_requirement_graph_blocks():
 g,a,o,m,i,v=setup_chain(); g.issues.append(RequirementIssue("x","error",("R1",),"invalid")); c=certify_requirement_to_verification_chain(g,a,o,m,i,v); assert not c.complete
