"""Cap-C Stage 2 — backend capability declarations and plan-id derivation."""

from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
    CompilationPlan,
    CompilationRequirement,
    PlannedCompilation,
    derive_plan_id,
)
from tiannara.domain.models.capability_manifest import BundleCapability


def _decl(
    capabilities: list[BundleCapability] | None = None,
    quality: float = 0.8,
    kinds=None,
):
    return BackendCapabilityDeclaration(
        backend_id="fastapi_hexagonal",
        artifact_kinds=kinds or [ArtifactKind.BACKEND_SERVICE],
        capabilities=capabilities or [
            BundleCapability.TEST,
            BundleCapability.HEALTH_CHECK,
        ],
        quality_profile=quality,
        metadata={"language": "python"},
    )


def test_artifact_kind_enum_is_extensible():
    assert ArtifactKind.BACKEND_SERVICE.value == "backend_service"


def test_derive_plan_id_is_deterministic_for_identical_inputs():
    req = CompilationRequirement(
        artifact_kind=ArtifactKind.BACKEND_SERVICE,
        required_capabilities=[BundleCapability.TEST, BundleCapability.CONTAINERIZE],
    )
    assert derive_plan_id([req], "default") == derive_plan_id([req], "default")


def test_derive_plan_id_differentiates_content_and_policy():
    base = CompilationRequirement(
        artifact_kind=ArtifactKind.BACKEND_SERVICE,
        required_capabilities=[BundleCapability.TEST],
    )
    extended = CompilationRequirement(
        artifact_kind=ArtifactKind.BACKEND_SERVICE,
        required_capabilities=[BundleCapability.TEST, BundleCapability.HEALTH_CHECK],
    )
    assert derive_plan_id([base], "default") != derive_plan_id([extended], "default")
    assert derive_plan_id([base], "default") != derive_plan_id([base], "relaxed")


def test_supports_true_when_all_capabilities_present():
    ok, missing = _decl().supports(
        ArtifactKind.BACKEND_SERVICE, [BundleCapability.TEST]
    )
    assert ok is True
    assert missing == []


def test_supports_reports_missing_capabilities():
    ok, missing = _decl(capabilities=[BundleCapability.TEST]).supports(
        ArtifactKind.BACKEND_SERVICE,
        [BundleCapability.TEST, BundleCapability.HEALTH_CHECK],
    )
    assert ok is False
    assert BundleCapability.HEALTH_CHECK in missing


def test_supports_rejects_unmatched_artifact_kind():
    ok, missing = _decl().supports(
        ArtifactKind.DEPLOYMENT, [BundleCapability.TEST]
    )
    assert ok is False
    assert BundleCapability.TEST in missing


def test_compilation_requirement_default_subject_ref_is_empty():
    req = CompilationRequirement(
        artifact_kind=ArtifactKind.BACKEND_SERVICE,
        required_capabilities=[BundleCapability.TEST],
    )
    assert req.subject_ref == ""


def test_plan_construction_holds_one_plan_per_requirement():
    requirement = CompilationRequirement(
        artifact_kind=ArtifactKind.BACKEND_SERVICE,
        required_capabilities=[BundleCapability.TEST],
    )
    plan = CompilationPlan(
        plan_id="p1",
        policy_name="default",
        planned=[
            PlannedCompilation(
                requirement=requirement, backend_id="b", declaration=_decl()
            )
        ],
    )
    assert len(plan.planned) == 1
