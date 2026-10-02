import pytest
from app.engine.requirement_ir import Requirement, RequirementKind, build_requirement_graph
from app.engine.requirement_isr import project_to_isr


def graph(*requirements):
    return build_requirement_graph(list(requirements))


def test_projection_preserves_source_traceability_and_is_technology_neutral():
    g = graph(Requirement("R1", "API request must authenticate", RequirementKind.SECURITY,
                          tags=("entity:Wallet",)))
    isr = project_to_isr(g)
    payload = isr.to_dict()
    assert payload["schema_version"] == "CAP-001-ISR.v1"
    assert payload["source_requirement_ids"] == ["R1"]
    assert payload["entities"][0]["name"] == "Wallet"
    assert payload["policies"][0]["source_requirements"] == ["R1"]
    assert all(v not in str(payload) for v in ("FastAPI", "React", "PostgreSQL", "AWS", "Docker"))


def test_explicit_invariant_is_projected():
    g = graph(Requirement("R1", "Transfer must not execute twice", RequirementKind.FUNCTIONAL))
    isr = project_to_isr(g)
    assert isr.invariants[0].invariant_id == "I-R1"


def test_invalid_requirement_graph_cannot_become_isr():
    g = graph(Requirement("R1", "Do X", RequirementKind.FUNCTIONAL, depends_on=("MISSING",)))
    with pytest.raises(ValueError, match="invalid requirements"):
        project_to_isr(g)


def test_interface_projection_is_conservative():
    g = graph(Requirement("R1", "The API request returns a response", RequirementKind.FUNCTIONAL))
    isr = project_to_isr(g)
    assert len(isr.interfaces) == 1
