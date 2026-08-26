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


BEHAVIORAL_STAGES: frozenset[TrialStage] = frozenset({
    TrialStage.BUILD,
    TrialStage.TEST,
    TrialStage.DEPLOY,
    TrialStage.RUNTIME,
    TrialStage.DESTROY,
    TrialStage.VERIFY,
})
