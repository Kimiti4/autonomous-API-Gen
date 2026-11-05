from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.domain.models.system_model import RequirementsReference, SystemModel

pytestmark = pytest.mark.skipif(
    shutil.which("mvn") is None or shutil.which("java") is None,
    reason="Spring Boot generated-project verification requires Java and Maven",
)


def test_generated_spring_boot_project_builds_and_passes_http_contract(tmp_path: Path):
    model = SystemModel(
        system_name="Generated Spring Boot Runtime",
        problem_statement="Verify generated Spring Boot application",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )
    result = build_compiler_registry().backend("spring_boot").generate(model)
    for relative, content in result.files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    tests = subprocess.run(
        ["mvn", "-B", "test"], cwd=tmp_path, check=False,
        timeout=900, capture_output=True, text=True,
    )
    assert tests.returncode == 0, tests.stdout + tests.stderr

    package = subprocess.run(
        ["mvn", "-B", "package", "-DskipTests"], cwd=tmp_path, check=False,
        timeout=600, capture_output=True, text=True,
    )
    assert package.returncode == 0, package.stdout + package.stderr

    if shutil.which("docker"):
        image = subprocess.run(
            ["docker", "build", "-t", "esap-generated-spring-boot-contract", "."],
            cwd=tmp_path, check=False, timeout=900, capture_output=True, text=True,
        )
        assert image.returncode == 0, image.stdout + image.stderr
