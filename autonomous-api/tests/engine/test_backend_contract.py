import pytest

from app.engine.backend_contract import (
    ARCHITECTURE_SCHEMA_VERSION,
    PYTHON_FASTAPI,
    BackendTarget,
    CompilationRequest,
    CompiledArtifact,
    make_compilation_request,
    validate_architecture,
)

VALID_ARCHITECTURE = {
    "services": ["users"],
    "auth": "api_key",
    "database": "sqlite",
    "cache_enabled": False,
    "rate_limiting": False,
    "cors_enabled": False,
    "logging_level": "",
    "api_version": "v1",
    "security_score": 1.0,
    "openapi_version": "3.0.0",
    "health_endpoints": True,
    "metrics_endpoints": False,
    "tracing_enabled": False,
    "circuit_breaker": False,
    "retry_policy": {},
    "timeout_config": {},
    "backends": [],
    "middleware": [],
    "security_policies": [],
}


def test_backend_target_is_explicit_and_neutral():
    assert PYTHON_FASTAPI.backend_id == "python-fastapi"
    assert PYTHON_FASTAPI.language == "python"
    assert PYTHON_FASTAPI.framework == "fastapi"


def test_compilation_request_keeps_architecture_separate_from_target():
    request = make_compilation_request(VALID_ARCHITECTURE)

    assert request.target == PYTHON_FASTAPI
    assert request.architecture == VALID_ARCHITECTURE
    assert "backend" not in request.architecture


def test_compilation_request_rejects_invalid_target():
    with pytest.raises(ValueError, match="backend_id"):
        CompilationRequest(BackendTarget("", "python", "fastapi"), VALID_ARCHITECTURE)


def test_compiled_artifact_is_explicitly_backend_owned():
    artifact = CompiledArtifact(
        backend_id="python-fastapi",
        files={"main.py": "from fastapi import FastAPI"},
        metadata={"architecture_hash": "example"},
    )
    assert artifact.backend_id == "python-fastapi"
    assert artifact.files["main.py"].startswith("from fastapi")


def test_architecture_drift_rejects_unknown_keys():
    drifted = dict(VALID_ARCHITECTURE)
    drifted["backdoor"] = "tampered"
    with pytest.raises(ValueError, match="drift"):
        validate_architecture(drifted)
    with pytest.raises(ValueError, match="drift"):
        make_compilation_request(drifted)


def test_architecture_drift_rejects_missing_required_keys():
    incomplete = {key: value for key, value in VALID_ARCHITECTURE.items() if key != "services"}
    with pytest.raises(ValueError, match="missing required key"):
        make_compilation_request(incomplete)


def test_architecture_drift_rejects_wrong_types():
    mistyped = dict(VALID_ARCHITECTURE)
    mistyped["services"] = "users"
    with pytest.raises(ValueError, match="type"):
        make_compilation_request(mistyped)


def test_request_carries_schema_version_boundary():
    request = make_compilation_request(VALID_ARCHITECTURE)
    assert request.architecture_schema == ARCHITECTURE_SCHEMA_VERSION