from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.domain.models.system_model import RequirementsReference, SystemModel


pytestmark = pytest.mark.skipif(
    shutil.which("ruby") is None or shutil.which("bundle") is None,
    reason="Rails generated-project verification requires Ruby and Bundler",
)


def test_generated_rails_project_installs_boots_and_passes_http_tests(tmp_path: Path):
    model = SystemModel(
        system_name="Generated Rails Runtime",
        problem_statement="Verify the emitted Rails framework runtime",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )
    result = build_compiler_registry().backend("rails").generate(model)
    for relative, content in result.files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    install = subprocess.run(
        ["bundle", "install"],
        cwd=tmp_path, check=False, timeout=600, capture_output=True, text=True,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    tests = subprocess.run(
        ["bundle", "exec", "rails", "test"],
        cwd=tmp_path, check=False, timeout=240, capture_output=True, text=True,
    )
    assert tests.returncode == 0, tests.stdout + tests.stderr

    about = subprocess.run(
        ["bundle", "exec", "rails", "about"],
        cwd=tmp_path, check=False, timeout=60, capture_output=True, text=True,
    )
    assert about.returncode == 0, about.stdout + about.stderr

    if shutil.which("docker"):
        image = subprocess.run(
            ["docker", "build", "-t", "esap-generated-rails-contract", "."],
            cwd=tmp_path, check=False, timeout=600, capture_output=True, text=True,
        )
        assert image.returncode == 0, image.stdout + image.stderr
