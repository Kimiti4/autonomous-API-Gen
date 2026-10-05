import pytest
from app.engine.requirement_architecture_bridge import derive_architecture_plan
from app.engine.requirement_ir import Requirement, RequirementKind, RequirementPriority, AcceptanceCriterion, build_requirement_graph
from app.engine.architecture_obligations import ArchitectureObligation

def graph(text="users can sign in"):
    return build_requirement_graph([Requirement("R-001",text,RequirementKind.FUNCTIONAL,RequirementPriority.MUST,(AcceptanceCriterion("AC-001","ok"),),(), "test")])

def test_requirement_links_to_architecture_obligation():
    o=ArchitectureObligation("O-1","R-001","authentication",("security",))
    p=derive_architecture_plan(graph(),{"R-001":(o,)})
    assert p.links[0].requirement_id=="R-001"

def test_missing_obligation_remains_unresolved():
    p=derive_architecture_plan(graph(),{})
    assert p.unresolved_requirement_ids==("R-001",)

def test_requirement_issues_fail_closed():
    g=build_requirement_graph([Requirement("R-001","must be fast and cheap",RequirementKind.NON_FUNCTIONAL,RequirementPriority.MUST,(),("ambiguous",),"test")])
    p=derive_architecture_plan(g,{"R-001":(ArchitectureObligation("O-1","R-001","perf",("performance",)),)})
    assert p.links==()
    assert p.unresolved_requirement_ids==("R-001",)
