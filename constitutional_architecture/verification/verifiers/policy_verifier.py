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


class PolicyVerifier(Verifier):
    @property
    def name(self) -> str:
        return "policy"

    @property
    def description(self) -> str:
        return "Verify policy declarations are complete and enforceable"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L3_SECURITY

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []
        isr = ctx.isr

        all_policies = [p for m in isr.system.modules for p in m.policies]

        for policy in all_policies:
            has_strategy = bool(policy.strategy)
            checks.append(VerificationCheck(
                check_id=f"POL-001-{policy.id}",
                name="policy_strategy",
                verifier=self.name,
                level=self.level,
                status=CheckStatus.PASSED if has_strategy else CheckStatus.WARNING,
                severity=CheckSeverity.WARNING,
                message=f"Policy '{policy.name}' strategy: {policy.strategy or 'undefined'}",
                isr_node_id=policy.id,
                isr_node_type="policy",
            ))

        all_permissions = [
            perm for p in all_policies for perm in p.permissions
        ]
        checks.append(VerificationCheck(
            check_id="POL-002",
            name="permissions_defined",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if all_permissions else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message=f"{len(all_permissions)} permission(s) defined",
        ))

        duration = (time.perf_counter() - start) * 1000
        success = all(c.passed or c.status == CheckStatus.WARNING for c in checks)
        return VerificationResult(
            verifier_name=self.name, level=self.level,
            checks=tuple(checks), duration_ms=duration, success=success,
        )
