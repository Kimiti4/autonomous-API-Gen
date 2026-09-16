import pytest

from app.engine.backend_contract import PYTHON_FASTAPI, make_compilation_request
from app.engine.backends import compile_architecture, get_backend


def test_python_backend_compiles_without_adding_backend_to_architecture():
    architecture = {
        "services": ["users"],
        "auth": "api_key",
        "database": "sqlite",
        "cache_enabled": False,
        "rate_limiting": False,
        "cors_enabled": False,
        "logging_level": "",
        "api_version": "v1",
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
    before = dict(architecture)
    artifact = compile_architecture(make_compilation_request(architecture))

    assert artifact.backend_id == PYTHON_FASTAPI.backend_id
    assert "main.py" in artifact.files
    assert architecture == before


def test_unknown_backend_fails_closed():
    with pytest.raises(ValueError, match="unknown compiler backend"):
        get_backend("unknown-backend")
