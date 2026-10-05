from app.engine.quality_requirements import evaluate_quality_requirements
from app.engine.requirement_ir import Requirement,RequirementKind,RequirementPriority,AcceptanceCriterion,build_requirement_graph

def g():
 return build_requirement_graph([
  Requirement("S-1","protect accounts",RequirementKind.SECURITY,RequirementPriority.MUST,(AcceptanceCriterion("A","x"),),tags=("auth",)),
  Requirement("P-1","protect personal data",RequirementKind.COMPLIANCE,RequirementPriority.MUST,(AcceptanceCriterion("A2","x"),),tags=("privacy",)),
 ])
def test_quality_requirements_are_first_class():
 r=evaluate_quality_requirements(g(),{"S-1":{"passed":True,"evidence_ids":("E1",)},"P-1":{"passed":True,"evidence_ids":("E2",)}})
 assert r.passed and r.requirement_ids==("P-1","S-1")
def test_missing_quality_evidence_fails():
 r=evaluate_quality_requirements(g(),{"S-1":{"passed":True,"evidence_ids":("E1",)},"P-1":{"passed":True}})
 assert not r.passed and r.missing_evidence==("P-1",)
