import os

import pytest

from app.engine.backend_contract import (
    ARCHITECTURE_SCHEMA_VERSION,
    BackendTarget,
    PYTHON_FASTAPI,
    make_compilation_request,
)
from app.engine.backends import compile_architecture, compile_and_materialize, get_backend

ARCHITECTURE = {
    "services": ["users", "orders"],
    "auth": "api_key",
    "database": "sqlite",
    "cache_enabled": True,
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


def test_python_backend_compiles_without_adding_backend_to_architecture():
    before = dict(ARCHITECTURE)
    artifact = compile_architecture(make_compilation_request(ARCHITECTURE))

    assert artifact.backend_id == PYTHON_FASTAPI.backend_id
    assert "main.py" in artifact.files
    assert ARCHITECTURE == before
    assert artifact.metadata["architecture_schema"] == ARCHITECTURE_SCHEMA_VERSION


def test_python_backend_emits_full_implementation_file_set():
    artifact = compile_architecture(make_compilation_request(ARCHITECTURE))

    expected = {
        "main.py",
        "database.py",
        "security.py",
        "requirements.txt",
        "Dockerfile",
        os.path.join("services", "models.py"),
        os.path.join("services", "__init__.py"),
        os.path.join("services", "users.py"),
        os.path.join("services", "orders.py"),
    }
    assert expected <= set(artifact.files)
    assert "class ResponseCacheMiddleware" in artifact.files["main.py"]


def test_python_backend_rejects_mismatched_schema_version():
    request = make_compilation_request(ARCHITECTURE)
    drifted = object.__new__(type(request))
    object.__setattr__(drifted, "target", request.target)
    object.__setattr__(drifted, "architecture", request.architecture)
    object.__setattr__(drifted, "architecture_schema", "genome-v0")

    backend = get_backend("python-fastapi")
    assert not backend.supports(drifted)
    with pytest.raises(ValueError, match="schema"):
        backend.compile(drifted)


def test_unknown_backend_fails_closed():
    with pytest.raises(ValueError, match="unknown compiler backend"):
        get_backend("unknown-backend")


def test_compile_and_materialize_writes_full_tree(tmp_path):
    output_dir = compile_and_materialize(ARCHITECTURE, str(tmp_path))

    assert os.path.isdir(os.path.join(output_dir, "services"))
    assert os.path.isfile(os.path.join(output_dir, "main.py"))
    assert os.path.isfile(os.path.join(output_dir, "Dockerfile"))
    assert os.path.isfile(os.path.join(output_dir, "services", "users.py"))
    assert os.path.isfile(os.path.join(output_dir, "services", "orders.py"))
    with open(os.path.join(output_dir, "services", "users.py"), encoding="utf-8") as f:
        assert "def list_items" in f.read()


def test_python_backend_rejects_other_targets():
    other = BackendTarget("go-gin", "go", "gin")
    request = make_compilation_request(ARCHITECTURE, target=other)
    backend = get_backend("python-fastapi")
    assert not backend.supports(request)
    with pytest.raises(ValueError, match="unsupported backend target"):
        backend.compile(request)