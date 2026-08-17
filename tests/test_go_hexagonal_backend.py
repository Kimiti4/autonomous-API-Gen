"""Phase 19 -- GoHexagonalBackend emission contract.

Asserts the second backend's generated shape (without running Go): the skeleton
files, the declared manifest (language=go + required capabilities), and the
backend-supplied build profile that the meta-compiler now reads.
"""
from __future__ import annotations

import pytest

from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.application.compiler.go_hexagonal_backend import GoHexagonalBackend
from tiannara.application.compiler.naming import slugify
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    DataModelSpec,
    FieldSpec,
    RequirementsReference,
    SystemModel,
)

STATEMENT_NAME = "Order Management"
EXPECTED_SLUG = slugify(STATEMENT_NAME)  # order_management


def _system_model() -> SystemModel:
    return SystemModel(
        system_name=STATEMENT_NAME,
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        data_models=[
            DataModelSpec(
                id="dm-order",
                name="order",
                owning_service_id="svc-1",
                fields=[
                    FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER),
                    FieldSpec(
                        name="total", type=AbstractFieldType.DECIMAL, required=True
                    ),
                ],
            )
        ],
    )


def _result():
    backend = GoHexagonalBackend()
    result = backend.generate(_system_model())
    return backend, result


def test_backend_id_and_slug():
    backend, result = _result()
    assert backend.backend_id == "go_hexagonal"
    assert backend.name == "go_hexagonal"
    assert result.system_name == EXPECTED_SLUG
    assert result.backend_id == "go_hexagonal"


def test_emits_expected_go_skeleton():
    _, result = _result()
    expected = [
        "go.mod",
        "cmd/server/main.go",
        "Dockerfile",
        "docker-compose.yml",
        ".github/workflows/ci.yml",
        "README.md",
        ".gitignore",
        "internal/domain/models.go",
        "internal/domain/repositories.go",
        "internal/application/services.go",
        "internal/infrastructure/memory.go",
        "internal/api/handlers.go",
        "internal/api/handlers_test.go",
    ]
    files = result.files
    for rel in expected:
        assert rel in files, f"missing generated file: {rel}"

    go_mod = files["go.mod"]
    assert go_mod.splitlines()[0].startswith("module github.com/tiannara/")
    assert "go 1.22" in go_mod

    models_go = files["internal/domain/models.go"]
    assert models_go.startswith("package domain")
    assert "type Order struct" in models_go
    # domain imports nothing outer.
    assert "internal/api" not in models_go
    assert "internal/application" not in models_go
    assert "internal/infrastructure" not in models_go


def test_capability_manifest_declares_go_contract():
    from tiannara.domain.models.capability_manifest import BundleCapability

    _, result = _result()
    cm = result.capability_manifest
    assert cm.backend_id == "go_hexagonal"
    assert cm.metadata["language"] == "go"
    assert cm.metadata["framework"] == "net/http"
    assert cm.metadata["style"] == "hexagonal"
    for cap in [
        BundleCapability.BUILD,
        BundleCapability.TEST,
        BundleCapability.HEALTH_CHECK,
        BundleCapability.CONTAINERIZE,
    ]:
        assert cm.provides(cap)


def test_build_profile_is_backend_supplied():
    backend, _ = _result()
    profile = backend.build_profile(STATEMENT_NAME)
    assert isinstance(profile, BackendBuildProfile)
    assert profile.language == "go"
    assert profile.verifier_kind == "go"
    assert "go.mod" in profile.required_files
    assert "cmd/server/main.go" in profile.required_files
    assert profile.build_command == ["go", "build", "./..."]
    assert profile.test_command == ["go", "test", "./..."]


def test_build_profile_declaration_registers_correctly():
    backend, _ = _result()
    decl = backend.build_profile_declaration()
    assert isinstance(decl, BackendCapabilityDeclaration)
    assert decl.backend_id == "go_hexagonal"
    assert ArtifactKind.BACKEND_SERVICE in decl.artifact_kinds
    assert decl.quality_profile == 0.80
    assert decl.metadata["language"] == "go"


# ---------------------------------------------------------------------------
# DEFECT-TRACKED: Go struct-tag emission for optional fields.
#
# R1 (Docker runtime) surfaced that the Go backend emitted a malformed struct
# tag for optional non-id fields: `` `json:"name,omitempty`` `` (stray backtick,
# missing closing quote) -> "string not terminated" -> build-failed. The Go
# static verifier (regex-based) does not compile, so this only appeared under a
# real `go test ./...`. The fix partitions the tag content cleanly; these tests
# pin the well-formed output and, when Docker is available, compile in-container.
# ---------------------------------------------------------------------------
def _model_with_optional_field() -> SystemModel:
    return SystemModel(
        system_name=STATEMENT_NAME,
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        data_models=[
            DataModelSpec(
                id="dm-order",
                name="order",
                owning_service_id="svc-1",
                fields=[
                    FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER),
                    FieldSpec(name="note", type=AbstractFieldType.TEXT, required=False),
                    FieldSpec(name="total", type=AbstractFieldType.DECIMAL, required=True),
                ],
            )
        ],
    )


def test_go_struct_tag_is_well_formed_for_optional_fields():
    backend = GoHexagonalBackend()
    result = backend.generate(_model_with_optional_field())
    models_go = result.files["internal/domain/models.go"]

    # Optional field -> `json:"note,omitempty"` with a properly closed tag.
    assert '`json:"note,omitempty"`' in models_go
    # Required field -> plain tag, no omitempty.
    assert '`json:"total"`' in models_go
    # The buggy form (stray backtick, unterminated) must be absent.
    assert '`json:"note,omitempty``' not in models_go
    assert '`json:"note,omitempty`' not in models_go
    # Balanced backticks across the file (every struct tag opens+closes).
    assert models_go.count("`") % 2 == 0


def _docker_available() -> bool:
    from tiannara.application.evolution.compiler_sandbox import docker_available
    return docker_available()


@pytest.mark.skipif(not _docker_available(), reason="docker + go toolchain required for runtime check")
def test_go_backend_bundle_compiles_and_tests_under_docker(tmp_path):
    import subprocess
    from tiannara.application.compiler.writer import write_bundle

    backend = GoHexagonalBackend()
    result = backend.generate(_model_with_optional_field())
    write_bundle(result, tmp_path)
    bundle = str(tmp_path)
    # `go test ./...` compiles every package (build + vet) and runs tests --
    # sufficient to prove the generated Go is valid, incl. optional-field tags.
    proc = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{bundle}:/work", "-w", "/work",
         "golang:1.22-alpine", "go", "test", "./..."],
        capture_output=True, text=True, timeout=240,
    )
    assert proc.returncode == 0, f"go test ./... failed:\n{proc.stdout}\n{proc.stderr}"

