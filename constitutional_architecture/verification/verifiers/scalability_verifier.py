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


class ScalabilityVerifier(Verifier):
    @property
    def name(self) -> str:
        return "scalability"

    @property
    def description(self) -> str:
        return "Verify horizontal scaling readiness"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L4_PERFORMANCE

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []
        isr = ctx.isr

        total_events = sum(len(m.events) for m in isr.system.modules)
        total_services = sum(len(m.services) for m in isr.system.modules)
        event_ratio = total_events / max(total_services, 1)
        checks.append(VerificationCheck(
            check_id="SCALE-001",
            name="event_driven_ratio",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if event_ratio > 0 else CheckStatus.WARNING,
            severity=CheckSeverity.INFO,
            message=f"Event/service ratio: {event_ratio:.2f}",
        ))

        total_deps = sum(len(m.dependencies) for m in isr.system.modules)
        module_count = isr.system.module_count
        dep_ratio = total_deps / max(module_count, 1)
        checks.append(VerificationCheck(
            check_id="SCALE-002",
            name="module_independence",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if dep_ratio <= 2.0 else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message=f"Average dependencies per module: {dep_ratio:.1f}",
        ))

        duration = (time.perf_counter() - start) * 1000
        return VerificationResult(
            verifier_name=self.name, level=self.level,
            checks=tuple(checks), duration_ms=duration, success=True,
        )
