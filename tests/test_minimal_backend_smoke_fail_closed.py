"""D07 regression: the minimal backend's smoke test exercises generated code.

The backend previously wrote ``assert True``. The generated suite now imports
the materialized health function and fails when that artifact is broken, so a
green smoke run is candidate-bound rather than vacuous.
"""

from __future__ import annotations

import subprocess
import sys

from tiannara.domain.models.genome import Genome
from tiannara.domain.models.intent import IntentSpecification
from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.infrastructure.backends.minimal_container_backend import (
    MinimalContainerBackend,
)


def _bundle(tmp_path):
    isr = IntermediateSoftwareRepresentation(
        system_id="d07",
        system_name="D07",
        intent=IntentSpecification(statement="demo", domain="general"),
    )
    return MinimalContainerBackend().compile(isr, Genome(), str(tmp_path / "out"))


def _run_smoke(bundle) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests"],
        cwd=bundle.path,
        capture_output=True,
        text=True,
    )


def test_smoke_suite_contains_no_vacuous_assertion(tmp_path):
    bundle = _bundle(tmp_path)
    smoke = (bundle.path / "tests" / "test_smoke.py").read_text(encoding="utf-8")

    assert "assert True" not in smoke
    assert "from app import health" in smoke
    assert "tests/test_smoke.py" in bundle.artifacts


def test_smoke_suite_passes_on_the_generated_app(tmp_path):
    bundle = _bundle(tmp_path)

    result = _run_smoke(bundle)

    assert result.returncode == 0, result.stdout + result.stderr


def test_smoke_suite_fails_when_the_artifact_is_broken(tmp_path):
    bundle = _bundle(tmp_path)
    app = bundle.path / "app.py"
    app.write_text(
        app.read_text(encoding="utf-8").replace("'ok'", "'broken'"),
        encoding="utf-8",
    )

    result = _run_smoke(bundle)

    assert result.returncode != 0
    assert "test_health_reports_ok" in result.stdout + result.stderr
