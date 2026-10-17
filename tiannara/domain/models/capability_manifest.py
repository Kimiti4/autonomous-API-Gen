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



class SemanticSupportLevel(str, enum.Enum):
    """Declared support is a claim to verify, not proof of enforcement."""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class ToolOperation(str, enum.Enum):
    """Operations an adapter can perform through its bounded toolchain."""

    INSPECT = "inspect"
    GENERATE = "generate"
    BUILD = "build"
    FORMAT = "format"
    LINT = "lint"
    TYPECHECK = "typecheck"
    TEST = "test"
    RUN = "run"
    PACKAGE = "package"
    SECURITY_SCAN = "security_scan"


class ToolchainCapabilityManifest(BaseModel):
    """Versioned, language-neutral declaration of an adapter's real toolchain.

    This describes discoverable tools and claimed semantic coverage. It is not
    evidence that a tool exists on the execution host or that a semantic is
    correctly enforced; those claims require a conformance run bound to the
    resolved executable versions and resulting artifact.
    """

    schema_version: str = "toolchain-capabilities.v1"
    adapter_id: str = Field(min_length=1, max_length=256)
    language: str = Field(min_length=1, max_length=128)
    compiler: str = Field(min_length=1, max_length=256)
    compiler_version_constraint: str = Field(min_length=1, max_length=128)
    runtime: str | None = None
    runtime_version_constraint: str | None = None
    target_platforms: tuple[str, ...] = ()
    operations: tuple[ToolOperation, ...] = ()
    semantic_support: dict[str, SemanticSupportLevel] = Field(default_factory=dict)
    required_toolchain_digests: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": True, "extra": "forbid"}

    @model_validator(mode="after")
    def validate_manifest(self):
        if not self.adapter_id.strip() or not self.language.strip() or not self.compiler.strip():
            raise ValueError("adapter, language, and compiler identifiers must be non-blank")
        if len(set(self.target_platforms)) != len(self.target_platforms):
            raise ValueError("target_platforms must be unique")
        if len(set(self.operations)) != len(self.operations):
            raise ValueError("operations must be unique")
        if any(not key.strip() for key in self.semantic_support):
            raise ValueError("semantic support keys must be non-blank")
        if any(not key.strip() or not value.strip() for key, value in self.required_toolchain_digests.items()):
            raise ValueError("toolchain digest names and values must be non-blank")
        if (self.runtime is None) != (self.runtime_version_constraint is None):
            raise ValueError("runtime and runtime_version_constraint must be supplied together")
        return self

    def supports_semantic(self, semantic: str) -> SemanticSupportLevel:
        """Missing semantics are UNKNOWN, never implicitly supported."""
        return self.semantic_support.get(semantic, SemanticSupportLevel.UNKNOWN)
