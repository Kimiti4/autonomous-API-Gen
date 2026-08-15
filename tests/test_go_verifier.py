"""Phase 19 -- GoBundleVerifier (deterministic, toolchain-free) + dispatch."""
from __future__ import annotations

from pathlib import Path

import pytest

from tiannara.application.compiler.build_profile import (
    RequiredFilesVerifier,
    make_verifier,
)
from tiannara.application.compiler.go_hexagonal_backend import GoHexagonalBackend
from tiannara.application.compiler.verification import (
    BundleVerificationReport,
    BundleVerifier,
    GoBundleVerifier,
)
from tiannara.application.compiler.writer import write_bundle
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    DataModelSpec,
    FieldSpec,
    RequirementsReference,
    SystemModel,
)

STATEMENT_NAME = "Order Management"


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
                        name="created", type=AbstractFieldType.TIMESTAMP, required=True
                    ),
                ],
            )
        ],
    )


def _clean_bundle(tmp_path: Path) -> Path:
    backend = GoHexagonalBackend()
    result = backend.generate(_system_model())
    root = write_bundle(result, str(tmp_path))
    return root


REQUIRED = ["go.mod", "cmd/server/main.go", "Dockerfile"]


def test_go_verifier_passes_on_clean_bundle(tmp_path):
    root = _clean_bundle(tmp_path)
    report = GoBundleVerifier(REQUIRED).verify(root)
    assert isinstance(report, BundleVerificationReport)
    assert report.ok is True
    assert report.missing_files == []
    assert report.syntax_errors == []
    assert report.dependency_violations == []


def test_go_verifier_flags_domain_importing_outer_package(tmp_path):
    root = _clean_bundle(tmp_path)
    # Sabotage: domain imports the api package -> violates inward dependency.
    sabotage = (
        'package domain\n'
        'import "github.com/tiannara/order_management/internal/api"\n'
        "//lint:ignore unused\n"
        "var _ = api.OrderHandler{}\n"
    )
    (root / "internal" / "domain" / "sabotage.go").write_text(sabotage, encoding="utf-8")
    report = GoBundleVerifier(REQUIRED).verify(root)
    assert report.ok is False
    assert report.dependency_violations
    assert any("internal/api" in v for v in report.dependency_violations)


def test_go_verifier_missing_required_file(tmp_path):
    root = _clean_bundle(tmp_path)
    (root / "Dockerfile").unlink()
    report = GoBundleVerifier(REQUIRED).verify(root)
    assert report.ok is False
    assert "Dockerfile" in report.missing_files


def test_go_verifier_missing_or_malformed_gomod(tmp_path):
    root = _clean_bundle(tmp_path)
    (root / "go.mod").write_text("bogus not a module", encoding="utf-8")
    report = GoBundleVerifier(REQUIRED).verify(root)
    assert report.ok is False
    assert report.syntax_errors
    assert any("go.mod" in e for e in report.syntax_errors)


def test_make_verifier_dispatches_on_language():
    py = make_verifier("python", package="order_management", required_files=["order_management/main.py"])
    assert isinstance(py, BundleVerifier)
    go = make_verifier("go", package="order_management", required_files=REQUIRED)
    assert isinstance(go, GoBundleVerifier)
    other = make_verifier("rust", package="order_management", required_files=[])
    assert isinstance(other, RequiredFilesVerifier)
    assert other.verify("/nonexistent").ok is True  # nothing required -> vacuously ok
