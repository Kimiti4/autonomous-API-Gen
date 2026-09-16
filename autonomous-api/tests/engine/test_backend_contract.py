from app.engine.backend_contract import (
    PYTHON_FASTAPI,
    CompilationRequest,
    CompiledArtifact,
    BackendTarget,
    make_compilation_request,
)


def test_backend_target_is_explicit_and_neutral():
    assert PYTHON_FASTAPI.backend_id == "python-fastapi"
    assert PYTHON_FASTAPI.language == "python"
    assert PYTHON_FASTAPI.framework == "fastapi"


def test_compilation_request_keeps_architecture_separate_from_target():
    architecture = {"services": ["users"], "authorization": "central-policy"}
    request = make_compilation_request(architecture)

    assert request.target == PYTHON_FASTAPI
    assert request.architecture == architecture
    assert "backend" not in request.architecture


def test_compilation_request_rejects_invalid_target():
    try:
        CompilationRequest(
            BackendTarget("", "python", "fastapi"),
            {"services": []},
        )
    except ValueError as exc:
        assert "backend_id" in str(exc)
    else:
        raise AssertionError("invalid backend target was accepted")


def test_compiled_artifact_is_explicitly_backend_owned():
    artifact = CompiledArtifact(
        backend_id="python-fastapi",
        files={"main.py": "from fastapi import FastAPI"},
        metadata={"architecture_hash": "example"},
    )
    assert artifact.backend_id == "python-fastapi"
    assert artifact.files["main.py"].startswith("from fastapi")
