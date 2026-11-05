from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.domain.models.system_model import RequirementsReference, SystemModel


pytestmark = pytest.mark.skipif(
    shutil.which("php") is None or shutil.which("composer") is None,
    reason="Laravel generated-project verification requires PHP and Composer",
)


def test_generated_laravel_project_installs_boots_and_passes_http_tests(tmp_path: Path):
    model = SystemModel(
        system_name="Generated Laravel Runtime",
        problem_statement="Verify the emitted framework runtime",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )
    result = build_compiler_registry().backend("laravel").generate(model)
    for relative, content in result.files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    subprocess.run(
        ["composer", "install", "--no-interaction", "--prefer-dist", "--no-progress"],
        cwd=tmp_path, check=True, timeout=600, capture_output=True, text=True,
    )
    subprocess.run(
        ["php", "artisan", "test"],
        cwd=tmp_path, check=True, timeout=180, capture_output=True, text=True,
    )
    subprocess.run(
        ["php", "artisan", "about"],
        cwd=tmp_path, check=True, timeout=60, capture_output=True, text=True,
    )
