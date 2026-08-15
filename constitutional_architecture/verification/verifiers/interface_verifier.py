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


class InterfaceVerifier(Verifier):
    @property
    def name(self) -> str:
        return "interface"

    @property
    def description(self) -> str:
        return "Verify API interface contracts"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L1_STATIC

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []
        isr = ctx.isr

        total_interfaces = sum(len(m.interfaces) for m in isr.system.modules)
        router_artifacts = [a for a in ctx.artifacts if "router" in a.path.lower()]

        checks.append(VerificationCheck(
            check_id="IFACE-001",
            name="interface_coverage",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if len(router_artifacts) >= total_interfaces else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message=f"{len(router_artifacts)} router(s) for {total_interfaces} interface(s)",
        ))

        total_endpoints = sum(
            len(iface.endpoints)
            for m in isr.system.modules
            for iface in m.interfaces
        )
        checks.append(VerificationCheck(
            check_id="IFACE-002",
            name="endpoint_coverage",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if total_endpoints > 0 else CheckStatus.WARNING,
            severity=CheckSeverity.INFO,
            message=f"{total_endpoints} endpoint(s) defined in ISR",
        ))

        duration = (time.perf_counter() - start) * 1000
        return VerificationResult(
            verifier_name=self.name,
            level=self.level,
            checks=tuple(checks),
            duration_ms=duration,
            success=True,
        )
