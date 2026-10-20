"""Build and exercise an actual generated React app with npm/Vitest/Vite."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from compiler.backends.react_frontend import ReactFrontendBackend
from tests.support.tor_sources import full_stack_plan


def _npm(*args: str) -> list[str]:
    executable = shutil.which("npm") or "npm"
    if os.name == "nt":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", executable, *args]
    return [executable, *args]


def test_generated_react_app_passes_vitest_and_production_build(tmp_path: Path):
    repo = ReactFrontendBackend().compile(full_stack_plan())
    for relative_path, content in repo.files.items():
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    subprocess.run(
        _npm("install", "--no-audit", "--no-fund"),
        cwd=tmp_path,
        check=True,
        timeout=600,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        _npm("test"),
        cwd=tmp_path,
        check=True,
        timeout=180,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        _npm("run", "build"),
        cwd=tmp_path,
        check=True,
        timeout=180,
        capture_output=True,
        text=True,
    )
    assert (tmp_path / "dist" / "index.html").is_file()
