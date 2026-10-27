"""Real generated Python and Rust behavioral builds and independent runtime tests."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend
from tests.support.execution_effect import executable_plan
from tests.support.tor_sources import authorized_backend_plan, backend_plan


def _write_repo(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def test_generated_python_app_runs_its_independent_behavior_suite(tmp_path: Path):
    repo = PythonFastAPIBackend().compile(backend_plan())
    root = tmp_path / "python-app"
    _write_repo(root, repo.files)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=root,
        check=True,
        timeout=600,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        check=True,
        timeout=180,
        capture_output=True,
        text=True,
    )


def test_generated_python_app_enforces_declared_authorization_policies(tmp_path: Path):
    """The generated runtime must enforce the declared policy, not just declare it."""
    repo = PythonFastAPIBackend().compile(authorized_backend_plan())
    root = tmp_path / "python-authorized-app"
    _write_repo(root, repo.files)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=root,
        check=True,
        timeout=600,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v"],
        cwd=root,
        check=False,
        timeout=180,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "test_denied_request_does_not_mutate_state" in result.stdout
    assert "test_authorization_denies_a_principal_without_a_grant" in result.stdout


def test_generated_python_app_enforces_the_executable_effect_contract(tmp_path: Path):
    """W12: authorization, pre/postconditions, and replay are enforced at runtime.

    The scenario file is authored independently of the emitter and copied into
    the generated repository, so passing it proves the generated runtime
    behaves as the contract states rather than merely declaring the contract.
    """
    repo = PythonFastAPIBackend().compile(executable_plan())
    root = tmp_path / "python-effect-app"
    _write_repo(root, repo.files)
    scenario = (
        Path(__file__).resolve().parents[1]
        / "support"
        / "effect_contract_scenario.py"
    )
    (root / "tests" / "test_effect_contract.py").write_text(
        scenario.read_text(encoding="utf-8"), encoding="utf-8"
    )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=root,
        check=True,
        timeout=600,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v"],
        cwd=root,
        check=False,
        timeout=180,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for name in (
        "test_authorized_execution_commits_once",
        "test_replay_returns_the_recorded_result_without_reexecution",
        "test_concurrent_same_key_requests_execute_once",
        "test_unauthorized_role_is_denied_without_execution_or_commit",
        "test_precondition_failure_is_rejected_without_execution_or_commit",
        "test_postcondition_failure_is_rejected_without_commit_and_retry_re_executes",
        "test_service_method_enforces_the_same_contract",
    ):
        assert name in result.stdout


def test_generated_rust_app_passes_cargo_tests(tmp_path: Path):
    repo = RustAxumBackend().compile(backend_plan())
    root = tmp_path / "rust-app"
    _write_repo(root, repo.files)
    subprocess.run(
        ["cargo", "test"],
        cwd=root,
        check=True,
        timeout=900,
        capture_output=True,
        text=True,
    )
    assert (root / "target" / "debug" / "deps").is_dir()
