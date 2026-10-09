"""Derive compilation requirements from the ISR (v2 rules).

Each rule maps ISR structure to a requirement. Rules are additive and
ADR-worthy. Selection is then performed over these requirements.

v2 adds the frontend, database, infrastructure, deployment, and documentation
rules -- each landed together with its backend family (never the rule without
a registered backend that can satisfy it). Rules are pure and registry-blind:
they read the SystemModel and return requirements; if a derived requirement
has no registered backend, selection fails loudly (BackendSelectionError)
rather than silently dropping the artifact kind.

This layer is pure: it does not touch any backend or registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    CompilationRequirement,
)
from tiannara.domain.models.capability_manifest import BundleCapability

if TYPE_CHECKING:
    from tiannara.domain.models.system_model import SystemModel


def derive_compilation_requirements(
    system_model: "SystemModel",
) -> list[CompilationRequirement]:
    requirements: list[CompilationRequirement] = []
    requirements.extend(_backend_service_requirements(system_model))
    requirements.extend(_frontend_requirements(system_model))
    requirements.extend(_database_requirements(system_model))
    requirements.extend(_infrastructure_requirements(system_model))
    requirements.extend(_deployment_requirements(system_model))
    requirements.extend(_documentation_requirements(system_model))
    return requirements


def _backend_service_requirements(
    system_model: "SystemModel",
) -> list[CompilationRequirement]:
    if not system_model.services:
        return []
    required = [
        BundleCapability.TEST,
        BundleCapability.HEALTH_CHECK,
        BundleCapability.CONTAINERIZE,
    ]
    return [
        CompilationRequirement(
            artifact_kind=ArtifactKind.BACKEND_SERVICE,
            required_capabilities=required,
            subject_ref="isr:services",
        )
    ]


def _frontend_requirements(
    system_model: "SystemModel",
) -> list[CompilationRequirement]:
    """A service-facing system gets a user-facing surface.

    Gated on services (never emitted for a model that compiles nothing).
    """
    if not system_model.services:
        return []
    return [
        CompilationRequirement(
            artifact_kind=ArtifactKind.FRONTEND_APPLICATION,
            required_capabilities=[BundleCapability.BUILD, BundleCapability.TEST],
            subject_ref="isr:services",
        )
    ]


def _database_requirements(
    system_model: "SystemModel",
) -> list[CompilationRequirement]:
    """Persisted entities get schema migration tooling.

    Gated on data models AND a service to own them: a migration without an
    owning service could never be exercised by the compiled system.
    """
    if not system_model.data_models or not system_model.services:
        return []
    return [
        CompilationRequirement(
            artifact_kind=ArtifactKind.DATABASE_MIGRATION,
            required_capabilities=[
                BundleCapability.DATABASE_MIGRATION,
                BundleCapability.TEST,
            ],
            subject_ref="isr:data_models",
        )
    ]


def _infrastructure_requirements(
    system_model: "SystemModel",
) -> list[CompilationRequirement]:
    if not system_model.services:
        return []
    return [
        CompilationRequirement(
            artifact_kind=ArtifactKind.INFRASTRUCTURE_PROVISION,
            required_capabilities=[
                BundleCapability.INFRASTRUCTURE_PROVISION,
                BundleCapability.BUILD,
                BundleCapability.TEST,
            ],
            subject_ref="isr:infrastructure",
        )
    ]


def _deployment_requirements(
    system_model: "SystemModel",
) -> list[CompilationRequirement]:
    if not system_model.services:
        return []
    return [
        CompilationRequirement(
            artifact_kind=ArtifactKind.DEPLOYMENT,
            required_capabilities=[
                BundleCapability.DEPLOY,
                BundleCapability.BUILD,
                BundleCapability.TEST,
            ],
            subject_ref="isr:deployment",
        )
    ]


def _documentation_requirements(
    system_model: "SystemModel",
) -> list[CompilationRequirement]:
    """Documented capabilities are a requirement of the model itself.

    Gated on capabilities or services so an empty model derives nothing.
    """
    if not system_model.capabilities and not system_model.services:
        return []
    return [
        CompilationRequirement(
            artifact_kind=ArtifactKind.DOCUMENTATION,
            required_capabilities=[
                BundleCapability.DOCUMENTATION,
                BundleCapability.TEST,
            ],
            subject_ref="isr:capabilities",
        )
    ]
