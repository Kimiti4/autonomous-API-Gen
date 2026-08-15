"""R2 -- technology-neutral failure observation contract.

A normalized, backend-agnostic record of a single backend failure, produced
*before* the Evolution Engine reasons about it. The engine consumes
``FailureObservation`` instances -- never raw compiler/test output -- so mutation
decisions carry only technology-neutral semantics (phase / category / severity).
"""
from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class FailurePhase(str, enum.Enum):
    """Ordered stage at which a backend can fail."""

    GENERATION = "generation"
    COMPILE = "compile"
    BUILD = "build"
    TEST = "test"
    RUNTIME = "runtime"
    PROBE = "probe"


class FailureCategory(str, enum.Enum):
    """Deterministic failure classes. The first Evolution Engine classifies
    without an LLM; these are the exhaustively enumerated buckets."""

    BUILD_FAILURE = "build_failure"
    TEST_FAILURE = "test_failure"
    TYPE_FAILURE = "type_failure"
    SYNTAX_FAILURE = "syntax_failure"
    DEPENDENCY_FAILURE = "dependency_failure"
    RUNTIME_FAILURE = "runtime_failure"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailureObservation(BaseModel):
    """Normalized, tamper-evident record of a backend failure.

    ``evidence_hash`` is a content-address over the normalized inputs (command,
    exit code, phase, artifacts, and a bounded diagnostic excerpt) so that two
    runs of the same failing command yield the same observation -- enabling
    regression detection and candidate dedup in the Evolution Engine.
    """

    execution_id: str
    backend_id: str
    phase: FailurePhase
    category: FailureCategory
    severity: Severity = Severity.MEDIUM
    command: list[str] = Field(default_factory=list)
    exit_code: int
    diagnostics: list[str] = Field(default_factory=list)
    affected_artifacts: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence_hash: str
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""

    @property
    def is_build_time(self) -> bool:
        return self.phase in (FailurePhase.COMPILE, FailurePhase.BUILD)
