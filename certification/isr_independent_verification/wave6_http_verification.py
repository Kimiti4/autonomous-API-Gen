"""W08 HTTP ingress adversarial slice (CP067-R6)."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

INDEPENDENT_VERIFIER_W08_HTTP = (
    "certification.isr_independent_verification.wave6_http_verification.v1"
)


@dataclass(frozen=True)
class Wave6HttpIngressReport:
    verifier_id: str
    passed: bool
    pytest_exit_code: int
    stdout_tail: str
    findings: tuple[str, ...]


def run_wave6_http_ingress_verification() -> Wave6HttpIngressReport:
    root = Path(__file__).resolve().parents[2]
    api_root = root / "autonomous-api"
    test_path = api_root / "tests" / "test_cp067_r5_http_ingress_adversarial.py"
    if not test_path.is_file():
        return Wave6HttpIngressReport(
            verifier_id=INDEPENDENT_VERIFIER_W08_HTTP,
            passed=False,
            pytest_exit_code=-1,
            stdout_tail="",
            findings=("http-test-missing",),
        )
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_path), "-q", "--tb=no"],
        cwd=str(api_root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    findings: tuple[str, ...] = ()
    if proc.returncode != 0:
        findings = (f"pytest-exit-{proc.returncode}",)
    tail = (proc.stdout or "")[-1500:]
    return Wave6HttpIngressReport(
        verifier_id=INDEPENDENT_VERIFIER_W08_HTTP,
        passed=proc.returncode == 0,
        pytest_exit_code=proc.returncode,
        stdout_tail=tail,
        findings=findings,
    )


def write_wave6_http_evidence(path: Path, report: Wave6HttpIngressReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "tiannara.cp067.wave6_http_ingress",
                "verifier_id": report.verifier_id,
                "passed": report.passed,
                "pytest_exit_code": report.pytest_exit_code,
                "findings": list(report.findings),
                "stdout_tail": report.stdout_tail,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
