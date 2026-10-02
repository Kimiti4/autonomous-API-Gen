from app.engine.architecture_ir import generate_baseline_candidates
from app.engine.architecture_obligations import (
    certify_architecture_mappings, derive_architecture_obligations, map_obligations,
)
from app.engine.requirement_ir import Requirement, RequirementKind, build_requirement_graph
from app.engine.requirement_isr import project_to_isr


def isr():
    return project_to_isr(build_requirement_graph([
        Requirement("R1", "Transfer must not execute twice", RequirementKind.FUNCTIONAL),
        Requirement("R2", "API request must authenticate", RequirementKind.SECURITY),
    ]))


def test_obligations_are_derived_from_explicit_isr_semantics():
    obs = derive_architecture_obligations(isr())
    assert [o.source_id for o in obs] == ["I-R1", "P-R2"]
    assert all(o.verification for o in obs)


def test_mapping_requires_explicit_satisfaction_and_evidence():
    obs = derive_architecture_obligations(isr())
    mappings = map_obligations(obs, ("COMP-CORE",), satisfied=True, rationale="explicit boundary")
    assert certify_architecture_mappings(obs, mappings) == ()


def test_missing_and_unsatisfied_mappings_fail():
    obs = derive_architecture_obligations(isr())
    mappings = map_obligations(obs[:1], (), satisfied=False, rationale="not supported")
    findings = certify_architecture_mappings(obs, mappings)
    assert any("missing obligation mapping" in x for x in findings)
    assert any("unsatisfied obligation" in x for x in findings)
    assert any("no component mapping" in x for x in findings)
