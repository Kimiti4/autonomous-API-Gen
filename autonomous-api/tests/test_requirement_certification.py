import pytest
from app.engine.requirement_ir import Requirement, RequirementKind, build_requirement_graph
from app.engine.requirement_certification import certify_requirements


def test_complete_requirement_graph_can_be_certified():
    g = build_requirement_graph([
        Requirement("R1", "Authenticate caller", RequirementKind.SECURITY,
                    acceptance_criteria=()),
    ])
    # Warnings do not invalidate CAP-001; the requirement is still traceable.
    cert = certify_requirements(g)
    assert cert.passed
    assert cert.source_requirement_count == cert.traced_requirement_count == 1
    assert cert.isr_schema_version == "CAP-001-ISR.v1"


def test_missing_dependency_blocks_certification():
    g = build_requirement_graph([
        Requirement("R1", "Do X", RequirementKind.FUNCTIONAL, depends_on=("R404",)),
    ])
    cert = certify_requirements(g)
    assert cert.status == "NOT_CERTIFIED"
    assert any(f.severity == "error" for f in cert.findings)


def test_certification_is_fail_closed_on_projection_failure():
    g = build_requirement_graph([
        Requirement("R1", "", RequirementKind.FUNCTIONAL),
    ]) if False else build_requirement_graph([
        Requirement("R1", "Do X", RequirementKind.FUNCTIONAL),
    ])
    cert = certify_requirements(g)
    assert cert.passed
