"""Runtime execution of the generated application's own test suite.

Authorization evidence is runtime evidence: the generated application must
install, start, and run its own adversarial suite. Static assertions about the
emitted source, unit tests on the emitter, mocked APIs, or a generic
authentication declaration are not authorization evidence and are never
accepted here.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from certification.authorization.candidate import sha256_json, sha256_text

_TEST_LINE = re.compile(
    r"^(?:.*::)?(?P<name>test_[A-Za-z0-9_:]+)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED)\b"
)


@dataclass(frozen=True)
class RuntimeReport:
    """The outcome of running the generated application's own suite."""

    passed: bool
    total: int
    failed: int
    passed_tests: tuple[str, ...]
    failed_tests: tuple[str, ...]
    required_tests: tuple[str, ...]
    missing_required: tuple[str, ...]
    stdout_sha256: str
    report_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "tiannara.authorization.runtime-report",
            "schema_version": "1.0.0",
            "passed": self.passed,
            "total": self.total,
            "failed": self.failed,
            "passed_tests": list(self.passed_tests),
            "failed_tests": list(self.failed_tests),
            "required_tests": list(self.required_tests),
            "missing_required": list(self.missing_required),
            "stdout_sha256": self.stdout_sha256,
            "report_hash": self.report_hash,
        }


def _report_hash(payload: Mapping[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "report_hash"}
    return sha256_json(body)


def write_repository(files: Mapping[str, str], root: Path) -> None:
    """Write the generated repository to disk."""
    for relative_path, content in files.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def run_generated_suite(
    files: Mapping[str, str],
    workdir: Path,
    required_tests: Sequence[str],
    *,
    install: bool = True,
) -> RuntimeReport:
    """Install and run the generated application's own suite.

    Returns the report; a failing suite is reported, not raised, so the caller
    can record the failure as evidence.
    """
    root = workdir / "generated-app"
    root.mkdir(parents=True, exist_ok=True)
    write_repository(files, root)

    if install:
        install_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
             "-r", "requirements.txt"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=900,
        )
        if install_result.returncode != 0:
            payload = {
                "schema_id": "tiannara.authorization.runtime-report",
                "schema_version": "1.0.0",
                "passed": False,
                "total": 0,
                "failed": 1,
                "passed_tests": [],
                "failed_tests": ["install"],
                "required_tests": list(required_tests),
                "missing_required": list(required_tests),
                "stdout_sha256": sha256_text(install_result.stdout + install_result.stderr),
            }
            payload["report_hash"] = _report_hash(payload)
            return RuntimeReport(
                passed=False,
                total=0,
                failed=1,
                passed_tests=(),
                failed_tests=("install",),
                required_tests=tuple(required_tests),
                missing_required=tuple(required_tests),
                stdout_sha256=payload["stdout_sha256"],
                report_hash=payload["report_hash"],
            )

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=900,
    )
    output = result.stdout + result.stderr
    passed_tests: list[str] = []
    failed_tests: list[str] = []
    for line in output.splitlines():
        match = _TEST_LINE.match(line.strip())
        if not match:
            continue
        name = match.group("name")
        if match.group("status") == "PASSED":
            passed_tests.append(name)
        else:
            failed_tests.append(name)
    missing = tuple(name for name in required_tests if name not in passed_tests)
    payload = {
        "schema_id": "tiannara.authorization.runtime-report",
        "schema_version": "1.0.0",
        "passed": result.returncode == 0 and not missing and not failed_tests,
        "total": len(passed_tests) + len(failed_tests),
        "failed": len(failed_tests),
        "passed_tests": sorted(passed_tests),
        "failed_tests": sorted(failed_tests),
        "required_tests": list(required_tests),
        "missing_required": list(missing),
        "stdout_sha256": sha256_text(output),
    }
    payload["report_hash"] = _report_hash(payload)
    return RuntimeReport(
        passed=payload["passed"],
        total=payload["total"],
        failed=payload["failed"],
        passed_tests=tuple(payload["passed_tests"]),
        failed_tests=tuple(payload["failed_tests"]),
        required_tests=tuple(required_tests),
        missing_required=missing,
        stdout_sha256=payload["stdout_sha256"],
        report_hash=payload["report_hash"],
    )
