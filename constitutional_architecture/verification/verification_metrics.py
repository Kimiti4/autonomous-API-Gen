from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerifierMetrics:
    executions: int = 0
    total_checks: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_duration_ms: float = 0.0

    @property
    def pass_rate(self) -> float:
        return self.total_passed / self.total_checks if self.total_checks > 0 else 0.0

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.executions if self.executions > 0 else 0.0


@dataclass
class VerificationMetrics:
    total_verifications: int = 0
    total_approvals: int = 0
    total_rejections: int = 0
    total_checks: int = 0
    total_repairs_recommended: int = 0
    avg_verification_ms: float = 0.0
    verifier_metrics: dict[str, VerifierMetrics] = field(default_factory=dict)
    level_distribution: dict[int, int] = field(default_factory=dict)

    @property
    def approval_rate(self) -> float:
        return self.total_approvals / self.total_verifications if self.total_verifications > 0 else 0.0

    def record_verification(
        self,
        approved: bool,
        duration_ms: float,
        check_count: int,
        level: int,
        repairs: int = 0,
    ) -> None:
        self.total_verifications += 1
        if approved:
            self.total_approvals += 1
        else:
            self.total_rejections += 1
        self.total_checks += check_count
        self.total_repairs_recommended += repairs
        self.level_distribution[level] = self.level_distribution.get(level, 0) + 1
        n = self.total_verifications
        self.avg_verification_ms = (self.avg_verification_ms * (n - 1) + duration_ms) / n

    def record_verifier(self, name: str, checks: int, passed: int, duration_ms: float) -> None:
        if name not in self.verifier_metrics:
            self.verifier_metrics[name] = VerifierMetrics()
        m = self.verifier_metrics[name]
        m.executions += 1
        m.total_checks += checks
        m.total_passed += passed
        m.total_failed += checks - passed
        m.total_duration_ms += duration_ms
