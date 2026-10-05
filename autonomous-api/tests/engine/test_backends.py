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

def test_go_backend_compiles_same_architecture_to_independent_artifact():
    from app.engine.backends import GoHTTPBackend

    request = make_compilation_request(
        {**ARCHITECTURE, "cache_enabled": False},
        target=GoHTTPBackend.target,
    )
    artifact = compile_architecture(request)

    assert artifact.backend_id == "go-nethttp"
    assert set(artifact.files) == {"go.mod", "main.go"}
    assert "package main" in artifact.files["main.go"]
    assert "http.ListenAndServe" in artifact.files["main.go"]
    assert "FastAPI" not in artifact.files["main.go"]


def test_go_backend_lowers_authentication_as_executable_semantics():
    from app.engine.backends import GoHTTPBackend

    expect = {
        "api_key": (["X-API-Key", "hmac.Equal", "http.StatusUnauthorized"], ["base64.StdEncoding", "Bearer "]),
        "basic": (["Basic ", "base64.StdEncoding.DecodeString", "hmac.Equal", "strings.TrimPrefix"], ["Bearer ", "sha256.New"]),
        "jwt": (["Bearer ", "hmac.New", "sha256.New", "RawURLEncoding", "json.Unmarshal", "time.Now"], ["Basic ", "X-API-Key"]),
    }
    for auth, (required, absent) in expect.items():
        request = make_compilation_request(
            {**ARCHITECTURE, "auth": auth, "cache_enabled": False},
            target=GoHTTPBackend.target,
        )
        main = compile_architecture(request).files["main.go"]
        for marker in required:
            assert marker in main, f"{auth}: expected {marker!r} in artifact"
        for marker in absent:
            assert marker not in main, f"{auth}: did not expect {marker!r} in artifact"


def test_go_backend_lowers_database_as_real_integration():
    from app.engine.backends import GoHTTPBackend

    request = make_compilation_request(
        {**ARCHITECTURE, "database": "sqlite", "cache_enabled": False},
        target=GoHTTPBackend.target,
    )
    artifact = compile_architecture(request)
    main = artifact.files["main.go"]
    assert 'sql.Open("sqlite", dsn)' in main
    assert "CREATE TABLE IF NOT EXISTS" in main
    assert 'db.Query("SELECT id, payload FROM records WHERE service = ?"' in main
    assert 'INSERT INTO records (service, payload) VALUES (?, ?)' in main
    assert '"database/sql"' in main
    assert '_ "modernc.org/sqlite"' in main
    assert "modernc.org/sqlite" in artifact.files["go.mod"]


def test_go_backend_lowers_cors_as_middleware_when_enabled():
    from app.engine.backends import GoHTTPBackend

    enabled = compile_architecture(
        make_compilation_request(
            {**ARCHITECTURE, "cors_enabled": True, "cache_enabled": False},
            target=GoHTTPBackend.target,
        )
    ).files["main.go"]
    assert "Access-Control-Allow-Origin" in enabled
    assert "Access-Control-Allow-Methods" in enabled
    assert "http.MethodOptions" in enabled
    assert 'withCORS(mux)' in enabled

    disabled = compile_architecture(
        make_compilation_request(
            {**ARCHITECTURE, "cors_enabled": False, "cache_enabled": False},
            target=GoHTTPBackend.target,
        )
    ).files["main.go"]
    assert "withCORS" not in disabled


def test_go_backend_serves_real_openapi_document():
    import json as jsonlib

    from app.engine.backends import GoHTTPBackend

    request = make_compilation_request(
        {**ARCHITECTURE, "cache_enabled": False},
        target=GoHTTPBackend.target,
    )
    main = compile_architecture(request).files["main.go"]
    assert 'Content-Type", "application/json"' in main
    assert 'const openAPIDoc = `' in main

    raw = main.split("const openAPIDoc = `", 1)[1].split("`", 1)[0]
    document = jsonlib.loads(raw)
    assert document["openapi"] == "3.0.0"
    assert document["info"]["title"] == "Generated API"
    for service in ARCHITECTURE["services"]:
        path = f"/api/{ARCHITECTURE['api_version']}/{service}"
        assert path in document["paths"]
        assert document["paths"][path]["get"]
        assert document["paths"][path]["post"]
    assert "/health" in document["paths"]
    assert "apikey_auth" in document["components"]["securitySchemes"]
    assert document["security"] == [{"apikey_auth": []}]


def test_go_backend_selection_is_explicit_and_fail_closed():
    request = make_compilation_request(
        {**ARCHITECTURE, "cache_enabled": True},
        target=BackendTarget("go-nethttp", "go", "net/http"),
    )
    with pytest.raises(ValueError, match="unmapped capabilities"):
        compile_architecture(request)


def test_go_backend_fails_closed_for_unsupported_database():
    request = make_compilation_request(
        {**ARCHITECTURE, "database": "postgres", "cache_enabled": False},
        target=BackendTarget("go-nethttp", "go", "net/http"),
    )
    with pytest.raises(ValueError, match="not lowerable by go-nethttp"):
        compile_architecture(request)


def test_go_backend_fails_closed_for_unsupported_auth():
    request = make_compilation_request(
        {**ARCHITECTURE, "auth": "oauth2", "cache_enabled": False},
        target=BackendTarget("go-nethttp", "go", "net/http"),
    )
    with pytest.raises(ValueError, match="not lowerable by go-nethttp"):
        compile_architecture(request)


def test_go_backend_compiles_and_executes_when_go_toolchain_available(tmp_path):
    import base64
    import hashlib
    import hmac as hmaclib
    import json as jsonlib
    import shutil
    import subprocess
    import time
    import urllib.request

    go = shutil.which("go")
    if go is None:
        for candidate in (
            r"C:\Program Files\Go\bin\go.exe",
            r"C:\Go\bin\go.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Go\bin\go.exe"),
        ):
            if os.path.isfile(candidate):
                go = candidate
                break
    if go is None:
        pytest.skip("go toolchain not installed; generated Go artifact not compiled at runtime")

    import app.engine.backends as backends_module

    request = make_compilation_request(
        {**ARCHITECTURE, "auth": "jwt", "cache_enabled": False},
        target=backends_module.GoHTTPBackend.target,
    )
    output_dir = compile_and_materialize(request.architecture, str(tmp_path), target=request.target)

    subprocess.run([go, "mod", "tidy"], cwd=output_dir, check=True, capture_output=True)
    subprocess.run([go, "build", "-o", "generated.exe", "."], cwd=output_dir, check=True, capture_output=True)

    server = subprocess.Popen(
        [os.path.join(output_dir, "generated.exe")],
        cwd=output_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 20
        while True:
            try:
                urllib.request.urlopen("http://localhost:8000/health", timeout=1)
                break
            except Exception:
                if time.time() > deadline:
                    raise AssertionError("generated Go server did not become ready")
                time.sleep(0.2)

        def b64url(data):
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

        header = b64url(jsonlib.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        payload = b64url(jsonlib.dumps({"sub": "user", "exp": int(time.time()) + 3600}).encode())
        signing_input = (header + "." + payload).encode()
        signature = b64url(
            hmaclib.new(b"generated-jwt-secret", signing_input, hashlib.sha256).digest()
        )
        token = header + "." + payload + "." + signature

        def request(path, bearer=None):
            headers = {"Authorization": "Bearer " + bearer} if bearer else {}
            req = urllib.request.Request("http://localhost:8000" + path, headers=headers)
            try:
                response = urllib.request.urlopen(req, timeout=5)
                return response.status, response.read()
            except urllib.error.HTTPError as error:
                return error.code, error.read()

        root_status, root_body = request("/")
        assert root_status == 200
        assert jsonlib.loads(root_body)["version"] == ARCHITECTURE["api_version"]

        health_status, _ = request("/health")
        assert health_status == 200

        openapi_status, openapi_body = request("/openapi.json")
        assert openapi_status == 200
        openapi_doc = jsonlib.loads(openapi_body)
        assert openapi_doc["openapi"] == "3.0.0"

        denied_status, _ = request("/api/v1/users")
        assert denied_status == 401

        create = urllib.request.Request(
            "http://localhost:8000/api/v1/users",
            data=jsonlib.dumps({"name": "alice"}).encode(),
            method="POST",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        )
        assert urllib.request.urlopen(create, timeout=5).status == 201

        listed_status, listed_body = request("/api/v1/users", token)
        assert listed_status == 200
        assert jsonlib.loads(listed_body)["items"] == [{"name": "alice"}]

        tampered = urllib.request.Request(
            "http://localhost:8000/api/v1/users",
            headers={"Authorization": "Bearer " + token.replace(token[-1], "x", 1)},
        )
        try:
            urllib.request.urlopen(tampered, timeout=5)
            assert False, "tampered token should be rejected"
        except urllib.error.HTTPError as error:
            assert error.code == 401
    finally:
        server.terminate()
        server.wait(timeout=10)


def test_backend_outputs_are_deterministic_for_same_architecture():
    request = make_compilation_request(
        {**ARCHITECTURE, "cache_enabled": False},
        target=BackendTarget("go-nethttp", "go", "net/http"),
    )
    first = compile_architecture(request)
    second = compile_architecture(request)

    assert first.files == second.files
    assert first.metadata == second.metadata
