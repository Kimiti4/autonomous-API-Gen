"""Phase-31 R2.4.0a -- FastAPIHexagonalBackend runtime contract (hermetic).

Asserts the FastAPI backend's fastapi-side mirror of the Go runtime declared in
R1: it now ships a ``runtime_image`` + injectable ``test_command`` and opts in to
a ``build_command`` (deps provisioning) via ``requires_build_phase``. Nothing
here pulls images: the docker cases stub the subprocess, and the gold-standard
real-docker case is skipped unless ``docker`` is on PATH.
"""
from __future__ import annotations

import asyncio
import shlex
from pathlib import Path

import pytest

from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.compiler.go_hexagonal_backend import GoHexagonalBackend
from tiannara.application.harness.calibration.generator import generate_corpus
from tiannara.application.harness.calibration.harness import (
    BackendCalibrationHarness,
    build_calibration_registry,
)
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger
from tiannara.infrastructure.sandbox import docker_environment as de
from tiannara.infrastructure.sandbox import local_environment as le
from tiannara.infrastructure.sandbox.docker_environment import DockerExecutionEnvironment
from tiannara.infrastructure.sandbox.local_environment import LocalExecutionEnvironment

STATEMENT_NAME = "Order System"


class _StubProc:
    """Minimal awaitable subprocess stand-in returning exit code 0."""

    stdout = None
    stderr = None

    async def wait(self, *a, **k):
        return 0

    async def read(self):
        return b""


def _bundle(tmp_path: Path) -> SystemDeploymentBundle:
    return SystemDeploymentBundle(
        project_id="order-system",
        backend_name="fastapi_hexagonal",
        isr_hash="",
        path=tmp_path / "out",
        artifacts=[],
        capability_manifest=None,
    )


# The backend's slugify lowercases via snake_case (spaces -> '_').
_SLUG = "order_system"
_TEST_CMD = ["python", "-m", "pytest", "-q", f"{_SLUG}/tests"]
_BUILD_CMD = ["python", "-m", "pip", "install", "-q", "-r", "requirements.txt", "-r", "requirements-dev.txt"]


# --- profile contract -------------------------------------------------------


def test_fastapi_profile_declares_runtime_image_and_build_phase():
    profile = FastAPIHexagonalBackend().build_profile(STATEMENT_NAME)
    assert profile.runtime_image == "python:3.12-slim"
    assert profile.requires_build_phase is True
    assert profile.build_command == _BUILD_CMD
    assert profile.test_command == _TEST_CMD
    # test_command is an injectable arg list, not a single shell string.
    assert profile.test_command[0] == "python"
    assert profile.test_command[1:3] == ["-m", "pytest"]
    assert profile.build_command[1:3] == ["-m", "pip"]


def test_go_profile_build_command_is_contract_only():
    """Go's image already carries the toolchain: build_command is verifier-only."""
    profile = GoHexagonalBackend().build_profile(STATEMENT_NAME)
    assert profile.requires_build_phase is False
    assert profile.build_command == ["go", "build", "./..."]


# --- environment composition (no real Docker) -------------------------------


def test_docker_env_composes_build_then_test_when_build_command(tmp_path, monkeypatch):
    captured: dict = {}

    async def fake(*cmd, **kw):
        captured["cmd"] = list(cmd)
        return _StubProc()

    monkeypatch.setattr(de.asyncio, "create_subprocess_exec", fake)

    env = DockerExecutionEnvironment(
        test_command=_TEST_CMD,
        runtime_image="python:3.12-slim",
        build_command=["python", "-m", "pip", "install", "-q", "-r", "requirements.txt"],
    )
    Path(tmp_path / "out").mkdir()
    asyncio.run(env.run_verification(_bundle(tmp_path)))

    cmd = captured["cmd"]
    assert cmd[:4] == ["docker", "run", "--rm", "-v"]
    host, sep, work = cmd[4].rpartition(":")
    assert sep == ":" and work == "/work"
    assert Path(host).is_absolute()  # mount-path invariant preserved
    assert cmd[5] == "-w" and cmd[6] == "/work"
    assert cmd[7] == "python:3.12-slim"
    # Single container entrypoint composes build && test.
    assert cmd[8] == "sh" and cmd[9] == "-c"
    assert cmd[10] == (
        shlex.join(["python", "-m", "pip", "install", "-q", "-r", "requirements.txt"])
        + " && "
        + shlex.join(_TEST_CMD)
    )


def test_docker_env_passes_test_command_bare_when_no_build_command(tmp_path, monkeypatch):
    """Go path: no build phase -> test_command passed bare (no sh -c)."""
    captured: dict = {}

    async def fake(*cmd, **kw):
        captured["cmd"] = list(cmd)
        return _StubProc()

    monkeypatch.setattr(de.asyncio, "create_subprocess_exec", fake)

    env = DockerExecutionEnvironment(
        test_command=["go", "test", "./..."],
        runtime_image="golang:1.22-alpine",
    )
    Path(tmp_path / "out").mkdir()
    asyncio.run(env.run_verification(_bundle(tmp_path)))

    cmd = captured["cmd"]
    assert cmd[:4] == ["docker", "run", "--rm", "-v"]
    assert cmd[7] == "golang:1.22-alpine"
    assert cmd[8:] == ["go", "test", "./..."]  # unchanged Go shape


def test_local_env_composes_build_then_test_when_build_command(tmp_path, monkeypatch):
    captured: dict = {}

    async def fake(*cmd, **kw):
        captured["cmd"] = list(cmd)
        return _StubProc()

    monkeypatch.setattr(le.asyncio, "create_subprocess_exec", fake)

    env = LocalExecutionEnvironment(
        test_command=_TEST_CMD,
        build_command=["python", "-m", "pip", "install", "-q", "-r", "requirements.txt"],
    )
    Path(tmp_path / "out").mkdir()
    asyncio.run(env.run_verification(_bundle(tmp_path)))

    cmd = captured["cmd"]
    assert cmd[0] == "sh" and cmd[1] == "-c"
    assert cmd[2] == (
        shlex.join(["python", "-m", "pip", "install", "-q", "-r", "requirements.txt"])
        + " && "
        + shlex.join(_TEST_CMD)
    )


# --- harness wiring ---------------------------------------------------------


def test_harness_runs_fastapi_in_docker_with_composed_build_phase(tmp_path, monkeypatch):
    """End-to-end: the harness passes FastAPI's build_command through to the env,
    producing a single ``sh -c "build && test"`` docker invocation that reports
    'ran' (subprocess stubbed -- no image is actually pulled here)."""
    import tiannara.application.harness.calibration.harness as H

    monkeypatch.setattr(H.DockerExecutionEnvironment, "available", classmethod(lambda cls: True))
    cmds: list[list[str]] = []

    async def fake(*cmd, **kw):
        cmds.append(list(cmd))
        return _StubProc()

    monkeypatch.setattr(H.asyncio, "create_subprocess_exec", fake)

    harness = BackendCalibrationHarness(
        build_calibration_registry(), JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    )
    report = harness.calibrate(corpus=generate_corpus(1, seed=0), out_root=tmp_path / "out")

    by_backend = {o.backend_id: o.runtime_status for o in report.outcomes}
    assert by_backend["go_hexagonal"] == "ran"
    assert by_backend["fastapi_hexagonal"] == "ran"
    assert report.runtime_coverage == 1.0

    fastapi_cmd = next(c for c in cmds if c[7] == "python:3.12-slim")
    assert fastapi_cmd[8] == "sh" and fastapi_cmd[9] == "-c"
    inner = fastapi_cmd[10]
    assert "pip install -q -r requirements.txt -r requirements-dev.txt" in inner
    assert "&&" in inner
    assert f"pytest -q {_SLUG}/tests" in inner


# --- gold-standard: real Docker, skipped when docker absent -----------------


@pytest.mark.docker_integration
@pytest.mark.skipif(
    DockerExecutionEnvironment.available() is False,
    reason="Docker not available; stubbed compose tests cover this path",
)
def test_fastapi_real_docker_pip_installs_and_runs_test_api(tmp_path):
    """Gold-standard: ``python:3.12-slim`` image, pip-install from the generated
    bundle's requirements files, run the backend's emitted test suite."""
    import shutil as _sh

    if _sh.which("docker") is None:
        pytest.skip("docker CLI not on PATH")

    profile = FastAPIHexagonalBackend().build_profile(STATEMENT_NAME)
    tests_dir = Path(profile.test_command[-1])  # <slug>/tests
    slug_dir = tests_dir.parent
    root = tmp_path / "bundle"
    (root / slug_dir / "tests").mkdir(parents=True)
    (root / slug_dir / "tests" / "test_smoke.py").write_text("def test_ok():\n    assert True\n")
    (root / slug_dir / "main.py").write_text("def test_ok():\n    assert True\n")
    (root / "requirements.txt").write_text("fastapi>=0.111\npydantic>=2.7\npytest\n")
    (root / "requirements-dev.txt").write_text("pytest\n")

    bundle = SystemDeploymentBundle(
        project_id="order-system",
        backend_name="fastapi_hexagonal",
        isr_hash="",
        path=root,
        artifacts=[],
        capability_manifest=None,
    )
    env = DockerExecutionEnvironment(
        test_command=profile.test_command,
        runtime_image=profile.runtime_image,
        build_command=profile.build_command,
    )
    result = asyncio.run(env.run_verification(bundle))
    assert result.exit_code == 0, f"runtime failed: see {result.logs_path}"
    assert result.passed
