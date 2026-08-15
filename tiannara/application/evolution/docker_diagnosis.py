"""R2.9.1 -- Docker failure diagnosis (classify before you fix).

Structured diagnosis of the four Docker-gated closed-loop failures that
blocked dynamic execution during R2.8.

Cardinal rule: classify before you fix. Every failure lands in exactly one
of three classes, and the class determines the remediation:

    ENVIRONMENT_GAP  -- infra/resource/env (daemon down, pull denied, OOM, ...)
    CODE_DEFECT      -- genuine logic error in artifact/orchestration
    TEST_DESIGN      -- flakiness, timing, load, isolation, detection weakness

The classification report is what clears the R2.8 quarantine block: it
replaces the earlier ``CONFIRMED_PRE_R28`` assertion with a diagnosed and
remediated record.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class FailureClass(str, Enum):
    ENVIRONMENT_GAP = "ENVIRONMENT_GAP"   # not engine code -- infra/resource/env
    CODE_DEFECT = "CODE_DEFECT"           # genuine logic error in artifact/orchestration
    TEST_DESIGN = "TEST_DESIGN"           # flakiness, timing, load, isolation, detection
    UNKNOWN = "UNKNOWN"


# Environment/infra signatures (superset of the R2.8 retry classifier).
_ENVIRONMENT = (
    "cannot connect to the docker daemon", "cannot connect to the docker api",
    "docker: command not found", "docker daemon is not running",
    "the system cannot find the file specified",
    "pull access denied", "no space left on device", "out of memory", "oom",
    "pip: command not found", "no module named", "connection refused",
    "network unreachable", "tls handshake", "image not found",
)
_TEST_DESIGN = (
    "deadline exceeded", "timed out", "timeout", "resource temporarily unavailable",
    "flaky", "pytest-timeout",
)


@dataclass(frozen=True)
class FailureDiagnosis:
    test_id: str
    failure_class: FailureClass
    matched_signature: str
    raw_signature: str


def classify(test_id: str, signature: str) -> FailureDiagnosis:
    lowered = signature.lower()
    for sig in _ENVIRONMENT:
        if sig in lowered:
            return FailureDiagnosis(test_id, FailureClass.ENVIRONMENT_GAP, sig, signature)
    for sig in _TEST_DESIGN:
        if sig in lowered:
            return FailureDiagnosis(test_id, FailureClass.TEST_DESIGN, sig, signature)
    # No infra/design signature -> treat as a genuine logic failure until proven otherwise.
    return FailureDiagnosis(test_id, FailureClass.CODE_DEFECT, "", signature)


# -- the R2.9.1 diagnosis report ------------------------------------------------

#: The four Docker-gated tests blocked during R2.8 (terminal signatures captured
#: while the daemon was down; all four share the same daemon-pipe signature).
_DOCKER_GATED_TESTS: tuple[str, ...] = (
    "tests/test_r24_closed_loop.py::test_r24_closed_loop_real_codegen_repair",
    "tests/test_r24_fastapi_runtime.py::test_fastapi_real_docker_pip_installs_and_runs_test_api",
    "tests/test_go_hexagonal_backend.py::test_go_backend_bundle_compiles_and_tests_under_docker",
    "tests/test_r26_competitive_evolution.py::test_r26_competitive_evolution_chooses_correct_repair",
)

_DAEMON_DOWN_SIGNATURE = (
    "failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; "
    "check if the path is correct and if the daemon is running: open "
    "//./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified."
)


@dataclass(frozen=True)
class DockerDiagnosisReport:
    """The R2.9.1 deliverable that clears the quarantine block."""

    diagnoses: tuple[FailureDiagnosis, ...]
    remediation: Mapping[str, str] = field(default_factory=dict)

    @property
    def all_environment_gap(self) -> bool:
        return all(d.failure_class is FailureClass.ENVIRONMENT_GAP for d in self.diagnoses)

    @property
    def failure_count(self) -> int:
        return len(self.diagnoses)

    @property
    def classes(self) -> Mapping[str, int]:
        counts: dict[str, int] = {}
        for d in self.diagnoses:
            counts[d.failure_class.value] = counts.get(d.failure_class.value, 0) + 1
        return counts


def diagnose_quarantine(
    test_ids: tuple[str, ...] = _DOCKER_GATED_TESTS,
    signature: str = _DAEMON_DOWN_SIGNATURE,
) -> DockerDiagnosisReport:
    """Diagnose the four R2.8-quarantined Docker failures.

    All four share the same captured terminal signature (daemon pipe missing),
    so each classifies as ENVIRONMENT_GAP: the Docker CLI was on PATH, so the
    tests ran instead of skipping, and failed at the daemon connection.
    """
    diagnoses = tuple(classify(tid, signature) for tid in test_ids)
    remediation = {
        FailureClass.ENVIRONMENT_GAP.value: (
            "Start the Docker daemon (Docker Desktop engine); no engine code change. "
            "Additionally harden the availability probe to ping the daemon so tests "
            "skip honestly when it is down instead of running-and-failing."
        ),
        FailureClass.CODE_DEFECT.value: (
            "Fix the actual logic in the closed-loop orchestration or artifact compilation."
        ),
        FailureClass.TEST_DESIGN.value: (
            "Fix the test: raise timeouts, improve isolation, extend retry policy."
        ),
    }
    return DockerDiagnosisReport(diagnoses, remediation)