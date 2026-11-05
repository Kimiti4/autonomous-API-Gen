from __future__ import annotations

import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.domain.models.system_model import RequirementsReference, SystemModel

pytestmark = pytest.mark.skipif(
    shutil.which("gradle") is None or shutil.which("java") is None,
    reason="Ktor generated-project verification requires Gradle and Java",
)


def test_generated_ktor_project_builds_tests_packages_and_serves_health(tmp_path: Path):
    model = SystemModel(
        system_name="Generated Ktor Runtime",
        problem_statement="Verify generated Ktor application",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )
    result = build_compiler_registry().backend("ktor").generate(model)
    for relative, content in result.files.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    build = subprocess.run(
        ["gradle", "test", "installDist", "--no-daemon"],
        cwd=tmp_path, check=False, timeout=900, capture_output=True, text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr

    if not shutil.which("docker"):
        pytest.skip("Docker unavailable; native Gradle build/test completed")

    image = "esap-generated-ktor-contract"
    built = subprocess.run(
        ["docker", "build", "-t", image, "."],
        cwd=tmp_path, check=False, timeout=900, capture_output=True, text=True,
    )
    assert built.returncode == 0, built.stdout + built.stderr

    container = subprocess.run(
        ["docker", "run", "-d", "-p", "18080:8080", image],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    try:
        last_error = None
        for _ in range(30):
            try:
                with urllib.request.urlopen("http://127.0.0.1:18080/health", timeout=3) as response:
                    assert response.status == 200
                    assert response.read().decode() == "ok"
                    return
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                time.sleep(2)
        pytest.fail(f"Generated Ktor container did not become healthy: {last_error}")
    finally:
        subprocess.run(["docker", "rm", "-f", container], check=False, capture_output=True)
