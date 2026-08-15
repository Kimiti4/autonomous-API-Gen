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


class RuntimeVerifier(Verifier):
    @property
    def name(self) -> str:
        return "runtime"

    @property
    def description(self) -> str:
        return "Runtime behaviour verification"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L4_PERFORMANCE

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []

        source_artifacts = ctx.get_artifacts_by_type("source")
        has_health = any("health" in a.content.lower() for a in source_artifacts)
        checks.append(VerificationCheck(
            check_id="RUNTIME-001",
            name="health_endpoint",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if has_health else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="Health endpoint found" if has_health else "No health endpoint in generated code",
        ))

        has_error_handling = any(
            "exception" in a.content.lower() or "error" in a.content.lower()
            or "try:" in a.content
            for a in source_artifacts
        )
        checks.append(VerificationCheck(
            check_id="RUNTIME-002",
            name="error_handling",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if has_error_handling else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="Error handling present" if has_error_handling else "No error handling detected",
        ))

        duration = (time.perf_counter() - start) * 1000
        return VerificationResult(
            verifier_name=self.name, level=self.level,
            checks=tuple(checks), duration_ms=duration, success=True,
        )
