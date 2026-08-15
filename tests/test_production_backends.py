"""
Tests for Phase 25.2 production compiler backends.
"""

from __future__ import annotations

import pytest

from compiler.backends.production.cicd_backend import GitHubActionsBackend
from compiler.backends.production.docker_backend import DockerDeploymentBackend
from compiler.backends.production.fastapi_backend import FastAPIFoundationBackend
from compiler.backends.production.openapi_backend import OpenAPIBackend
from compiler.backends.production.postgres_backend import PostgresSchemaBackend
from compiler.registry import BackendRegistry
from compiler.sdk.certification import BackendCertificationEngine
from compiler.sdk.models import BackendCertificationRequest
from compiler.sdk.testing import run_backend_contract_tests


PRODUCTION_BACKENDS = [
    OpenAPIBackend(),
    PostgresSchemaBackend(),
    FastAPIFoundationBackend(),
    DockerDeploymentBackend(),
    GitHubActionsBackend(),
]


@pytest.mark.parametrize("backend", PRODUCTION_BACKENDS)
def test_production_backend_passes_contract_tests(backend):
    passed, results, output = run_backend_contract_tests(backend)

    assert passed, results
    assert output is not None
    assert output.artifacts


@pytest.mark.parametrize("backend", PRODUCTION_BACKENDS)
def test_production_backend_is_certifiable(backend):
    registry = BackendRegistry()
    registry.register_backend(backend)

    engine = BackendCertificationEngine(registry)

    report = engine.certify(
        BackendCertificationRequest(
            backend_id=backend.manifest.backend_id,
        )
    )

    assert report.status.value == "CERTIFIED", report
    assert report.contract_tests_passed
    assert report.determinism_passed
    assert report.validation_passed
