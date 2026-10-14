"""Conformance-facing tests for technology-neutral toolchain manifests."""
import pytest
from pydantic import ValidationError

from tiannara.domain.models.capability_manifest import (
    SemanticSupportLevel,
    ToolOperation,
    ToolchainCapabilityManifest,
)
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)


def manifest(**overrides):
    values = {
        "adapter_id": "python-uv",
        "language": "Python",
        "compiler": "CPython",
        "compiler_version_constraint": ">=3.11,<3.14",
        "runtime": "CPython",
        "runtime_version_constraint": ">=3.11,<3.14",
        "target_platforms": ("linux-x86_64", "windows-x86_64"),
        "operations": (ToolOperation.BUILD, ToolOperation.TEST, ToolOperation.RUN),
        "semantic_support": {
            "authorization.workspace_isolation": SemanticSupportLevel.PARTIAL,
            "relational.atomicity": SemanticSupportLevel.SUPPORTED,
        },
        "required_toolchain_digests": {"CPython": "sha256:" + "a" * 64},
    }
    values.update(overrides)
    return ToolchainCapabilityManifest(**values)


def test_missing_semantic_is_unknown_not_supported():
    declared = manifest()
    assert declared.supports_semantic("authorization.workspace_isolation") is SemanticSupportLevel.PARTIAL
    assert declared.supports_semantic("cryptography.key_rotation") is SemanticSupportLevel.UNKNOWN


def test_manifest_rejects_duplicate_operations_and_targets():
    with pytest.raises(ValidationError, match="operations must be unique"):
        manifest(operations=(ToolOperation.TEST, ToolOperation.TEST))
    with pytest.raises(ValidationError, match="target_platforms must be unique"):
        manifest(target_platforms=("linux-x86_64", "linux-x86_64"))


def test_runtime_and_version_constraint_must_be_declared_together():
    with pytest.raises(ValidationError, match="must be supplied together"):
        manifest(runtime="CPython", runtime_version_constraint=None)


def test_legacy_backend_declaration_remains_compatible_but_manifest_is_explicit():
    legacy = BackendCapabilityDeclaration(
        backend_id="legacy-python",
        artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
        capabilities=[],
    )
    assert legacy.toolchain_manifest is None

    described = BackendCapabilityDeclaration(
        backend_id="python-uv",
        artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
        capabilities=[],
        toolchain_manifest=manifest(),
    )
    assert described.toolchain_manifest.adapter_id == "python-uv"
