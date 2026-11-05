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

    install = subprocess.run(
        ["composer", "install", "--no-interaction", "--prefer-dist", "--no-progress"],
        cwd=tmp_path, check=False, timeout=600, capture_output=True, text=True,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    feature_tests = subprocess.run(
        ["php", "artisan", "test"],
        cwd=tmp_path, check=False, timeout=180, capture_output=True, text=True,
    )
    assert feature_tests.returncode == 0, feature_tests.stdout + feature_tests.stderr
    about = subprocess.run(
        ["php", "artisan", "about"],
        cwd=tmp_path, check=False, timeout=60, capture_output=True, text=True,
    )
    assert about.returncode == 0, about.stdout + about.stderr

    if shutil.which("docker"):
        image = "esap-generated-laravel-contract"
        built = subprocess.run(
            ["docker", "build", "-t", image, "."],
            cwd=tmp_path, check=False, timeout=900, capture_output=True, text=True,
        )
        assert built.returncode == 0, built.stdout + built.stderr
        container = subprocess.run(
            ["docker", "run", "-d", "-p", "18081:8000", image],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        try:
            last_error = None
            for _ in range(30):
                try:
                    with urllib.request.urlopen("http://127.0.0.1:18081/api/health", timeout=3) as response:
                        assert response.status == 200
                        assert b'"status":"ok"' in response.read().replace(b" ", b"")
                        return
                except (urllib.error.URLError, TimeoutError) as exc:
                    last_error = exc
                    time.sleep(2)
            pytest.fail(f"Generated Laravel container did not become healthy: {last_error}")
        finally:
            subprocess.run(["docker", "rm", "-f", container], check=False, capture_output=True)
