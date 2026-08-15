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


class ComplianceVerifier(Verifier):
    @property
    def name(self) -> str:
        return "compliance"

    @property
    def description(self) -> str:
        return "Verify compliance and governance requirements"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L3_SECURITY

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []

        isr = ctx.isr
        has_audit = any(
            "audit" in p.name.lower() or "audit" in p.policy_type.value.lower()
            for m in isr.system.modules for p in m.policies
        )
        checks.append(VerificationCheck(
            check_id="COMP-001",
            name="audit_logging",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if has_audit else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="Audit logging policy defined" if has_audit else "No audit logging policy",
        ))

        has_retention = any(
            "retention" in p.name.lower() or "retention" in p.policy_type.value.lower()
            for m in isr.system.modules for p in m.policies
        )
        checks.append(VerificationCheck(
            check_id="COMP-002",
            name="data_retention",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if has_retention else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="Data retention policy defined" if has_retention else "No data retention policy",
        ))

        duration = (time.perf_counter() - start) * 1000
        return VerificationResult(
            verifier_name=self.name, level=self.level,
            checks=tuple(checks), duration_ms=duration, success=True,
        )
