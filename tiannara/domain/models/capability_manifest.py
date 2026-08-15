"""Capability manifest — the contract between compiler backends and
meta-compilers.

Constitutional rule encoded here: meta-compilers (CI/CD, repository
materializer, deployment) match CAPABILITIES, never backend identifiers.
`backend_id` is carried purely as provenance for evidence/telemetry; the
backend-coupling guard prohibits its use in meta-compiler selection logic.

Naming note: BundleCapability (compiled artifact) is distinct from AIR's
CapabilityDeclaration (reasoning backend). Two vocabularies, two domains —
deliberately never merged.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class BundleCapability(str, enum.Enum):
    """Canonical capability vocabulary for compiled artifacts.

    Extension rule: adding a capability is additive and ADR-worthy;
    renaming or removing one is a schema-version change.
    """

    BUILD = "build"                                # assemble sources into artifacts
    LINT = "lint"                                  # style/consistency checks
    STATIC_ANALYSIS = "static_analysis"            # deep analysis beyond lint
    TEST = "test"                                  # executable verification suite
    SECURITY_SCAN = "security_scan"                # automated security analysis
    CONTAINERIZE = "containerize"                  # container image buildable
    DATABASE_MIGRATION = "database_migration"      # schema migration tooling
    INFRASTRUCTURE_PROVISION = "infrastructure_provision"  # IaC applicable
    DEPLOY = "deploy"                              # deployable unit produced
    HEALTH_CHECK = "health_check"                  # liveness/readiness surface
    OBSERVABILITY = "observability"                # logs/metrics/traces wiring
    DOCUMENTATION = "documentation"                # generated docs present
    RELEASE = "release"                            # release/packaging metadata


class CapabilityManifest(BaseModel):
    """Emitted by every compiler backend alongside its bundle."""

    schema_version: str = "1.0"
    backend_id: str = Field(min_length=1)   # provenance only — never for matching
    capabilities: list[BundleCapability] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _unique_capabilities(self) -> "CapabilityManifest":
        values = [capability.value for capability in self.capabilities]
        if len(values) != len(set(values)):
            duplicates = sorted({v for v in values if values.count(v) > 1})
            raise ValueError(f"duplicate capabilities: {duplicates}")
        return self

    def provides(self, capability: BundleCapability) -> bool:
        return capability in self.capabilities


class CapabilityContractError(ValueError):
    """Raised when meta-compilation requires a manifest a bundle lacks."""
