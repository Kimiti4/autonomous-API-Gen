from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum, Enum, unique
from typing import Any


@unique
class VerificationLevel(IntEnum):
    L0_ARCHITECTURAL = 0
    L1_STATIC = 1
    L2_BEHAVIOURAL = 2
    L3_SECURITY = 3
    L4_PERFORMANCE = 4
    L5_OPERATIONAL = 5
    L6_PRODUCTION = 6

    def __str__(self) -> str:
        return self.name

    @property
    def requires_compilation(self) -> bool:
        return self >= VerificationLevel.L1_STATIC

    @property
    def requires_deployment(self) -> bool:
        return self >= VerificationLevel.L4_PERFORMANCE

    @property
    def description(self) -> str:
        descriptions = {
            VerificationLevel.L0_ARCHITECTURAL: "ISR-level architectural verification",
            VerificationLevel.L1_STATIC: "Static analysis of generated source",
            VerificationLevel.L2_BEHAVIOURAL: "Test execution and behavioural verification",
            VerificationLevel.L3_SECURITY: "Security policy and vulnerability analysis",
            VerificationLevel.L4_PERFORMANCE: "Performance verification in sandbox",
            VerificationLevel.L5_OPERATIONAL: "Operational verification in staging",
            VerificationLevel.L6_PRODUCTION: "Continuous production verification",
        }
        return descriptions[self]


@unique
class CheckSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    BLOCKER = "blocker"

    def __str__(self) -> str:
        return self.value

    @property
    def blocks_deployment(self) -> bool:
        return self in {CheckSeverity.CRITICAL, CheckSeverity.BLOCKER}

    @property
    def blocks_approval(self) -> bool:
        return self in {CheckSeverity.ERROR, CheckSeverity.CRITICAL, CheckSeverity.BLOCKER}


@unique
class CheckStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class VerificationCheck:
    check_id: str
    name: str
    verifier: str
    level: VerificationLevel
    status: CheckStatus
    severity: CheckSeverity = CheckSeverity.ERROR
    message: str = ""
    details: str = ""
    isr_node_id: str = ""
    isr_node_type: str = ""
    artifact_path: str = ""
    requirement_id: str = ""
    suggested_repair: str = ""
    repair_confidence: float = 0.0
    repair_mutation_type: str = ""
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == CheckStatus.PASSED

    @property
    def blocks_deployment(self) -> bool:
        return not self.passed and self.severity.blocks_deployment

    @property
    def explanation(self) -> str:
        parts = [
            f"[{self.check_id}] {self.name}: {self.status.value.upper()}",
        ]
        if self.message:
            parts.append(f"  Message: {self.message}")
        if self.isr_node_id:
            parts.append(f"  ISR Node: {self.isr_node_type} '{self.isr_node_id}'")
        if self.artifact_path:
            parts.append(f"  Artifact: {self.artifact_path}")
        if self.suggested_repair:
            parts.append(f"  Suggested Repair: {self.suggested_repair}")
            parts.append(f"  Confidence: {self.repair_confidence:.2f}")
        return "\n".join(parts)


@dataclass(frozen=True)
class VerificationResult:
    verifier_name: str
    level: VerificationLevel
    checks: tuple[VerificationCheck, ...] = ()
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.status != CheckStatus.SKIPPED)

    @property
    def warning_count(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.WARNING)

    @property
    def has_blockers(self) -> bool:
        return any(c.blocks_deployment for c in self.checks)

    @property
    def all_checks_passed(self) -> bool:
        return all(c.passed or c.status == CheckStatus.WARNING for c in self.checks)
