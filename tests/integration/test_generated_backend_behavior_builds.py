"""Real generated Python and Rust behavioral builds and independent runtime tests."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend
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
