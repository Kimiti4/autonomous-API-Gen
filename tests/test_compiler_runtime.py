"""
Tests for Phase 25 Universal Software Compiler runtime.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from compiler.api import create_app
from compiler.backends.reference_backend import ReferenceBackend
from compiler.errors import BackendNotFoundError, ISRValidationError
from compiler.kernel import UniversalCompiler
from compiler.models import CompilationRequest, CompilationTarget
from compiler.registry import BackendRegistry


def minimal_isr() -> dict:
    return {
        "isr_id": "isr_billing_001",
        "version": "1.0.0",
        "name": "Billing System",
        "domains": [
            {
                "name": "billing",
                "services": [
                    {
                        "name": "BillingService",
                        "apis": [
                            {
                                "name": "createInvoice"
                            }
                        ],
                    }
                ],
            }
        ],
        "events": [
            {
                "name": "InvoiceCreated"
            }
        ],
        "data_models": [
            {
                "name": "Invoice"
            }
        ],
    }


def build_compiler(tmp_path: Path) -> UniversalCompiler:
    registry = BackendRegistry()
    registry.register_backend(ReferenceBackend())

    return UniversalCompiler(
        registry=registry,
        output_root=tmp_path,
    )


def test_compile_succeeds(tmp_path: Path) -> None:
    compiler = build_compiler(tmp_path)

    request = CompilationRequest(
        isr=minimal_isr(),
        target=CompilationTarget(
            backend_id="reference.summary",
        ),
    )

    result = compiler.compile(request)

    assert result.status == "SUCCEEDED"
    assert result.artifact_manifest is not None
    assert result.artifact_manifest.files

    output_directory = tmp_path / result.job_id

    for artifact_file in result.artifact_manifest.files:
        artifact_path = output_directory / artifact_file.path
        assert artifact_path.exists()

    manifest_path = output_directory / "artifact-manifest.json"
    assert manifest_path.exists()


def test_invalid_isr_fails_validation(tmp_path: Path) -> None:
    compiler = build_compiler(tmp_path)

    invalid_isr = minimal_isr()
    del invalid_isr["version"]

    request = CompilationRequest(
        isr=invalid_isr,
        target=CompilationTarget(
            backend_id="reference.summary",
        ),
    )

    with pytest.raises(ISRValidationError):
        compiler.compile(request)


def test_unknown_backend_fails(tmp_path: Path) -> None:
    compiler = build_compiler(tmp_path)

    request = CompilationRequest(
        isr=minimal_isr(),
        target=CompilationTarget(
            backend_id="missing.backend",
        ),
    )

    with pytest.raises(BackendNotFoundError):
        compiler.compile(request)


def test_api_compile(tmp_path: Path) -> None:
    app = create_app(output_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/v1/compiler/compile",
        json={
            "isr": minimal_isr(),
            "target": {
                "backend_id": "reference.summary",
            },
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "SUCCEEDED"
    assert body["artifact_manifest"]["files"]


def test_api_invalid_isr(tmp_path: Path) -> None:
    app = create_app(output_root=tmp_path)
    client = TestClient(app)

    invalid_isr = minimal_isr()
    del invalid_isr["version"]

    response = client.post(
        "/v1/compiler/compile",
        json={
            "isr": invalid_isr,
            "target": {
                "backend_id": "reference.summary",
            },
        },
    )

    assert response.status_code == 422

    body = response.json()

    assert body["message"] == "ISR validation failed."
    assert body["report"]["valid"] is False


def test_api_backend_discovery(tmp_path: Path) -> None:
    app = create_app(output_root=tmp_path)
    client = TestClient(app)

    response = client.post(
        "/v1/compiler/backends/discover",
        json={
            "artifact_types": ["markdown"],
        },
    )

    assert response.status_code == 200

    backends = response.json()

    backend_ids = {backend["backend_id"] for backend in backends}

    assert "reference.summary" in backend_ids