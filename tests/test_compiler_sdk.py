"""
Tests for Phase 25.1 Compiler Backend SDK and certification.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from compiler.api import create_default_compiler
from compiler.backends.reference_backend import ReferenceBackend
from compiler.errors import ArtifactPackagingError
from compiler.models import (
    BackendCapabilities,
    BackendManifest,
    CompilationOutput,
)
from compiler.registry import BackendRegistry
from compiler.sdk.artifacts import CompilationOutputBuilder
from compiler.sdk.certification import BackendCertificationEngine
from compiler.sdk.models import BackendCertificationRequest
from compiler.sdk.routes import router as sdk_router
from compiler.sdk.testing import (
    default_test_isr,
    run_backend_contract_tests,
)


class BrokenBackend:
    """Backend that produces no artifacts."""

    def __init__(self) -> None:
        self.manifest = BackendManifest(
            backend_id="broken.backend",
            name="Broken Backend",
            version="0.1.0",
            description="Backend used to test certification failure.",
            capabilities=BackendCapabilities(
                supported_targets=["test"],
                artifact_types=["text"],
            ),
        )

    def compile(self, context):
        return CompilationOutput(artifacts=[])


def build_sdk_app(tmp_path: Path) -> FastAPI:
    compiler = create_default_compiler(tmp_path)

    app = FastAPI()
    app.state.compiler = compiler
    app.state.certification_engine = BackendCertificationEngine(
        compiler.registry
    )
    app.include_router(sdk_router)

    return app


def test_output_builder_rejects_reserved_path():
    builder = CompilationOutputBuilder()

    with pytest.raises(ArtifactPackagingError):
        builder.add_artifact("artifact-manifest.json", "content")


def test_output_builder_rejects_parent_traversal():
    builder = CompilationOutputBuilder()

    with pytest.raises(ArtifactPackagingError):
        builder.add_artifact("../escape.txt", "content")


def test_output_builder_sorts_artifacts():
    builder = CompilationOutputBuilder()

    builder.add_artifact("b.txt", "B")
    builder.add_artifact("a.txt", "A")

    output = builder.build()

    assert output.artifacts[0].path == "a.txt"
    assert output.artifacts[1].path == "b.txt"


def test_reference_backend_passes_contract_tests():
    backend = ReferenceBackend()

    passed, results, output = run_backend_contract_tests(backend)

    assert passed, results
    assert output is not None
    assert output.artifacts


def test_broken_backend_fails_contract_tests():
    backend = BrokenBackend()

    passed, results, output = run_backend_contract_tests(backend)

    assert not passed
    assert output is None or not output.artifacts


def test_certification_engine_certifies_reference_backend():
    registry = BackendRegistry()
    registry.register_backend(ReferenceBackend())

    engine = BackendCertificationEngine(registry)

    report = engine.certify(
        BackendCertificationRequest(
            backend_id="reference.summary",
        )
    )

    assert report.status.value == "CERTIFIED"
    assert report.contract_tests_passed
    assert report.determinism_passed
    assert report.validation_passed


def test_certification_engine_fails_broken_backend():
    registry = BackendRegistry()
    registry.register_backend(BrokenBackend())

    engine = BackendCertificationEngine(registry)

    report = engine.certify(
        BackendCertificationRequest(
            backend_id="broken.backend",
        )
    )

    assert report.status.value == "FAILED"
    assert not report.contract_tests_passed


def test_api_certify_and_revoke(tmp_path: Path):
    app = build_sdk_app(tmp_path)
    client = TestClient(app)

    certify_response = client.post(
        "/v1/compiler/sdk/certify",
        json={
            "backend_id": "reference.summary",
        },
    )

    assert certify_response.status_code == 200

    certify_body = certify_response.json()

    assert certify_body["status"] == "CERTIFIED"

    list_response = client.get("/v1/compiler/sdk/certifications")

    assert list_response.status_code == 200

    reports = list_response.json()

    assert any(
        report["backend_id"] == "reference.summary"
        for report in reports
    )

    revoke_response = client.post(
        "/v1/compiler/sdk/certifications/reference.summary/revoke",
        json={
            "reason": "Testing revocation.",
        },
    )

    assert revoke_response.status_code == 200

    revoke_body = revoke_response.json()

    assert revoke_body["status"] == "REVOKED"
    assert revoke_body["revocation_reason"] == "Testing revocation."