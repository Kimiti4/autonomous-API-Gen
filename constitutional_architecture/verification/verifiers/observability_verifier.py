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


class ObservabilityVerifier(Verifier):
    @property
    def name(self) -> str:
        return "observability"

    @property
    def description(self) -> str:
        return "Verify observability configuration"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L5_OPERATIONAL

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []
        isr = ctx.isr

        deployment = isr.system.deployment
        if deployment:
            monitoring = deployment.monitoring
            checks.append(VerificationCheck(
                check_id="OBS-001", name="metrics_enabled",
                verifier=self.name, level=self.level,
                status=CheckStatus.PASSED if monitoring.metrics_enabled else CheckStatus.WARNING,
                severity=CheckSeverity.WARNING,
                message="Metrics enabled" if monitoring.metrics_enabled else "Metrics not enabled",
            ))
            checks.append(VerificationCheck(
                check_id="OBS-002", name="tracing_enabled",
                verifier=self.name, level=self.level,
                status=CheckStatus.PASSED if monitoring.tracing_enabled else CheckStatus.WARNING,
                severity=CheckSeverity.WARNING,
                message="Tracing enabled" if monitoring.tracing_enabled else "Tracing not enabled",
            ))
            checks.append(VerificationCheck(
                check_id="OBS-003", name="structured_logging",
                verifier=self.name, level=self.level,
                status=CheckStatus.PASSED if monitoring.structured_logging else CheckStatus.WARNING,
                severity=CheckSeverity.WARNING,
                message="Structured logging enabled" if monitoring.structured_logging else "No structured logging",
            ))
        else:
            checks.append(VerificationCheck(
                check_id="OBS-000", name="no_deployment",
                verifier=self.name, level=self.level,
                status=CheckStatus.SKIPPED, severity=CheckSeverity.INFO,
                message="No deployment config; observability check skipped",
            ))

        duration = (time.perf_counter() - start) * 1000
        return VerificationResult(
            verifier_name=self.name, level=self.level,
            checks=tuple(checks), duration_ms=duration, success=True,
        )
