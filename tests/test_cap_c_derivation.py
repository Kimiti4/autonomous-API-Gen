"""Cap-C Stage 2 — ISR-driven compilation requirement derivation (v1 rules)."""

import copy

import pytest

from tiannara.application.compiler.derivation import derive_compilation_requirements
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.capability_manifest import BundleCapability
from tiannara.domain.models.system_model import (
    DataModelSpec,
    FieldSpec,
    AbstractFieldType,
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


def test_derivation_emits_current_artifact_requirements_for_services():
    requirements = derive_compilation_requirements(_system_model_with_service())
    by_kind = {requirement.artifact_kind: requirement for requirement in requirements}

    assert set(by_kind) == {
        ArtifactKind.BACKEND_SERVICE,
        ArtifactKind.FRONTEND_APPLICATION,
        ArtifactKind.INFRASTRUCTURE_PROVISION,
        ArtifactKind.DEPLOYMENT,
        ArtifactKind.DOCUMENTATION,
    }
    backend_requirement = by_kind[ArtifactKind.BACKEND_SERVICE]
    assert BundleCapability.TEST in backend_requirement.required_capabilities
    assert BundleCapability.HEALTH_CHECK in backend_requirement.required_capabilities
    assert BundleCapability.CONTAINERIZE in backend_requirement.required_capabilities
    assert backend_requirement.subject_ref == "isr:services"


def test_documentation_requirement_is_derived_for_named_system_without_services():
    requirements = derive_compilation_requirements(_empty_system_model())
    assert len(requirements) == 1
    assert requirements[0].artifact_kind is ArtifactKind.DOCUMENTATION
    assert requirements[0].subject_ref == "isr:documentation"


def test_database_migration_requirement_is_derived_for_data_models():
    model = _empty_system_model().model_copy(
        update={
            "data_models": [
                DataModelSpec(
                    id="order",
                    name="Order",
                    owning_service_id="svc-order",
                    fields=[FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER)],
                )
            ]
        }
    )
    requirements = derive_compilation_requirements(model)
    by_kind = {requirement.artifact_kind: requirement for requirement in requirements}
    assert ArtifactKind.DATABASE_MIGRATION in by_kind
    assert BundleCapability.DATABASE_MIGRATION in by_kind[ArtifactKind.DATABASE_MIGRATION].required_capabilities


def test_derivation_is_pure_does_not_mutate_input():
    model = _system_model_with_service()
    snapshot = copy.deepcopy(model)
    derive_compilation_requirements(model)
    assert model == snapshot


def test_derived_requirements_are_selectable_by_real_backend():
    from tiannara.application.compiler.registry import CompilerRegistry
    from tiannara.application.compiler.selector import (
        BackendSelectionError,
        plan_compilation,
    )
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
    # The backend is eligible for the backend-service requirement, but the
    # complete artifact plan must fail until all other required artifact kinds
    # have a registered compatible backend.
    with pytest.raises(BackendSelectionError):
        plan_compilation(
            registry, derive_compilation_requirements(_system_model_with_service())
        )
    plan = plan_compilation(
        registry,
        [r for r in derive_compilation_requirements(_system_model_with_service())
         if r.artifact_kind is ArtifactKind.BACKEND_SERVICE],
    )
    assert len(plan.planned) == 1
    assert plan.planned[0].backend_id == "fastapi_hexagonal"
