from __future__ import annotations

import time

from constitutional_architecture.verification.verification_context import VerificationContext
from constitutional_architecture.verification.verification_result import (
    CheckSeverity,
    CheckStatus,
    VerificationCheck,
    VerificationLevel,
    VerificationResult,
)
from constitutional_architecture.verification.verifiers.verifier_interface import Verifier


class PerformanceVerifier(Verifier):
    @property
    def name(self) -> str:
        return "performance"

    @property
    def description(self) -> str:
        return "Verify performance characteristics"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L4_PERFORMANCE

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []
        isr = ctx.isr

        total_services = sum(len(m.services) for m in isr.system.modules)
        stateless = sum(
            1 for m in isr.system.modules for s in m.services if s.is_stateless
        )
        ratio = stateless / total_services if total_services > 0 else 1.0
        checks.append(VerificationCheck(
            check_id="PERF-001",
            name="statelessness_ratio",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if ratio >= 0.8 else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message=f"Statelessness ratio: {ratio:.0%} ({stateless}/{total_services})",
        ))

        has_scaling = isr.system.deployment is not None
        checks.append(VerificationCheck(
            check_id="PERF-002",
            name="scaling_configured",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if has_scaling else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="Scaling configuration present" if has_scaling else "No scaling configuration",
        ))

        duration = (time.perf_counter() - start) * 1000
        return VerificationResult(
            verifier_name=self.name, level=self.level,
            checks=tuple(checks), duration_ms=duration, success=True,
        )
