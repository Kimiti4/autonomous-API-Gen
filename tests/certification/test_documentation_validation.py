from tiannara.application.compiler.documentation import validate_generated_documentation


def test_documentation_must_match_isr_identity_and_provenance():
    result = validate_generated_documentation(
        readme="# TaskFlow\n\nGenerated from the technology-neutral ISR.\n\nCapabilities: task scheduling",
        system_name="TaskFlow",
        required_capabilities=("task scheduling",),
    )
    assert result.passed


def test_documentation_rejects_wrong_software_identity():
    result = validate_generated_documentation(
        readme="# InventoryApp\n\nGenerated from the technology-neutral ISR.",
        system_name="TaskFlow",
    )
    assert "SYSTEM_NAME_MISMATCH" in result.blockers


def test_documentation_rejects_unverified_claims_and_placeholders():
    result = validate_generated_documentation(
        readme="# TaskFlow\n\nGenerated from the technology-neutral ISR.\n\nTODO: finish API.\nProduction ready.",
        system_name="TaskFlow",
    )
    assert "PLACEHOLDER_DOCUMENTATION" in result.blockers
    assert "UNVERIFIED_RUNTIME_CLAIM" in result.blockers


def test_documentation_rejects_missing_provenance():
    result = validate_generated_documentation(
        readme="# TaskFlow\n\nA task application.",
        system_name="TaskFlow",
    )
    assert "PROVENANCE_MISSING" in result.blockers
