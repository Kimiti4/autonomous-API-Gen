"""Cap-C Stage 2 — ISR-driven compilation requirement derivation (v1 rules)."""

import copy

from tiannara.application.compiler.derivation import derive_compilation_requirements
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.capability_manifest import BundleCapability
from tiannara.domain.models.system_model import (
    RequirementsReference,
    ServiceSpec,
    SystemModel,
)


def _system_model_with_service() -> SystemModel:
    return SystemModel(
        system_name="Order Service",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        services=[
            ServiceSpec(
                id="svc-1",
                name="order",
                domain_id="general",
                responsibilities=["fulfil orders"],
            )
        ],
    )


def _empty_system_model() -> SystemModel:
    return SystemModel(
        system_name="Empty",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )


def test_derivation_emits_backend_service_requirement_for_services():
    requirements = derive_compilation_requirements(_system_model_with_service())
    assert len(requirements) == 1
    requirement = requirements[0]
    assert requirement.artifact_kind is ArtifactKind.BACKEND_SERVICE
    assert BundleCapability.TEST in requirement.required_capabilities
    assert BundleCapability.HEALTH_CHECK in requirement.required_capabilities
    assert BundleCapability.CONTAINERIZE in requirement.required_capabilities


def test_derivation_empty_when_no_services():
    assert derive_compilation_requirements(_empty_system_model()) == []


def test_derivation_is_pure_does_not_mutate_input():
    model = _system_model_with_service()
    snapshot = copy.deepcopy(model)
    derive_compilation_requirements(model)
    assert model == snapshot


def test_backend_requirement_subject_ref_references_isr_services():
    requirements = derive_compilation_requirements(_system_model_with_service())
    assert requirements[0].subject_ref == "isr:services"


def test_derived_requirements_are_selectable_by_real_backend():
    from tiannara.application.compiler.registry import CompilerRegistry
    from tiannara.application.compiler.selector import plan_compilation
    from tiannara.application.compiler.fastapi_hexagonal_backend import (
        FastAPIHexagonalBackend,
    )

    registry = CompilerRegistry()
    registry.register(
        FastAPIHexagonalBackend(),
        BackendCapabilityDeclaration(
            backend_id="fastapi_hexagonal",
            artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=[
                BundleCapability.BUILD,
                BundleCapability.LINT,
                BundleCapability.STATIC_ANALYSIS,
                BundleCapability.TEST,
                BundleCapability.SECURITY_SCAN,
                BundleCapability.CONTAINERIZE,
                BundleCapability.DEPLOY,
                BundleCapability.HEALTH_CHECK,
                BundleCapability.OBSERVABILITY,
                BundleCapability.DOCUMENTATION,
                BundleCapability.RELEASE,
            ],
            quality_profile=0.8,
            metadata={"language": "python", "framework": "fastapi"},
        ),
    )
    plan = plan_compilation(
        registry, derive_compilation_requirements(_system_model_with_service())
    )
    assert len(plan.planned) == 1
    assert plan.planned[0].backend_id == "fastapi_hexagonal"
