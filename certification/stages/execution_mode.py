"""Execution mode — the anti-vacuity mechanism for stage execution.

Every behavioral stage records an explicit ExecutionMode. The verifier refuses
CERTIFIED unless the mode equals the configured required mode — so a stub can
never silently substitute for Docker.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from certification.core.trial import TrialStage


class ExecutionMode(str, Enum):
    REAL_DOCKER = "real_docker"
    STUB = "stub"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class StageExecution:
    stage: TrialStage
    mode: ExecutionMode
    passed: bool
    duration_s: float
    logs_hash: str
    image_digest: str = ""
    container_id: str = ""
    peak_resource: str = ""
    detail: str = ""
    retries: int = 0
    retry_signatures: tuple[str, ...] = ()
    failure_class: str = ""
    # Startup readiness WAITS are distinct from retry amplification: they are
    # the bounded number of health polls a slow-starting container consumed.
    # They are recorded here (independently observable/bounded) and are NOT
    # counted as retry_executions/retry_rate.
    startup_polls: int = 0
    startup_wait_s: float = 0.0


BEHAVIORAL_STAGES: frozenset[TrialStage] = frozenset({
    TrialStage.BUILD,
    TrialStage.TEST,
    TrialStage.DEPLOY,
    TrialStage.RUNTIME,
    TrialStage.DESTROY,
    TrialStage.VERIFY,
})
