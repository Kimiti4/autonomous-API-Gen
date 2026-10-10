"""Derive compilation requirements from the ISR (v1 rules).

Each rule maps ISR structure to a requirement. Rules are additive and
ADR-worthy. Selection is then performed over these requirements. v1 covers
backend services only; frontend, database, infrastructure, deployment, and
documentation rules arrive together with their backend families — never
before, never without a matching backend.

This layer is pure: it reads the SystemModel and returns requirements. It does
not touch any backend or registry.
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
    # Future rules (each lands with its backend family):
    #   _frontend_requirements(system_model)
    #   _database_requirements(system_model)
    #   _infrastructure_requirements(system_model)
    #   _deployment_requirements(system_model)
    #   _documentation_requirements(system_model)
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

def _frontend_requirements(system_model: "SystemModel") -> list[CompilationRequirement]:
    if not (system_model.capabilities or system_model.apis or system_model.services):
        return []
    return [CompilationRequirement(
        artifact_kind=ArtifactKind.FRONTEND_APPLICATION,
        required_capabilities=[BundleCapability.BUILD, BundleCapability.TEST],
        subject_ref="isr:frontend",
    )]


def _database_requirements(system_model: "SystemModel") -> list[CompilationRequirement]:
    if not system_model.data_models:
        return []
    return [CompilationRequirement(
        artifact_kind=ArtifactKind.DATABASE_MIGRATION,
        required_capabilities=[BundleCapability.DATABASE_MIGRATION, BundleCapability.TEST],
        subject_ref="isr:data_models",
    )]


def _infrastructure_requirements(system_model: "SystemModel") -> list[CompilationRequirement]:
    if not system_model.services:
        return []
    return [CompilationRequirement(
        artifact_kind=ArtifactKind.INFRASTRUCTURE_PROVISION,
        required_capabilities=[BundleCapability.INFRASTRUCTURE_PROVISION],
        subject_ref="isr:infrastructure",
    )]


def _deployment_requirements(system_model: "SystemModel") -> list[CompilationRequirement]:
    if not system_model.services:
        return []
    return [CompilationRequirement(
        artifact_kind=ArtifactKind.DEPLOYMENT,
        required_capabilities=[BundleCapability.DEPLOY, BundleCapability.HEALTH_CHECK],
        subject_ref="isr:deployment",
    )]


def _documentation_requirements(system_model: "SystemModel") -> list[CompilationRequirement]:
    if not system_model.system_name:
        return []
    return [CompilationRequirement(
        artifact_kind=ArtifactKind.DOCUMENTATION,
        required_capabilities=[BundleCapability.DOCUMENTATION, BundleCapability.TEST],
        subject_ref="isr:documentation",
    )]
