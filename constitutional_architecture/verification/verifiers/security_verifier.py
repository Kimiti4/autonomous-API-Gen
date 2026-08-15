from __future__ import annotations

import re
import time

from constitutional_architecture.isr.model.policy import PolicyType
from constitutional_architecture.verification.verification_context import VerificationContext
from constitutional_architecture.verification.verification_result import (
    CheckSeverity,
    CheckStatus,
    VerificationCheck,
    VerificationLevel,
    VerificationResult,
)
from constitutional_architecture.verification.verifiers.verifier_interface import Verifier


class SecurityVerifier(Verifier):
    SECRET_PATTERNS = [
        re.compile(r"(?i)(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"(?i)bearer\s+[a-zA-Z0-9\-._~+/]{20,}"),
        re.compile(r"(?i)-----BEGIN\s+(RSA\s+)?PRIVATE KEY-----"),
    ]

    @property
    def name(self) -> str:
        return "security"

    @property
    def description(self) -> str:
        return "Security policy and vulnerability verification"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L3_SECURITY

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []
        isr = ctx.isr

        checks.append(self._check_auth_policy_exists(isr))
        checks.append(self._check_authorization_defined(isr))
        checks.append(self._check_interfaces_secured(isr))

        if ctx.has_artifacts:
            checks.append(self._check_no_hardcoded_secrets(ctx))
            checks.append(self._check_input_validation(ctx))

        duration = (time.perf_counter() - start) * 1000
        success = all(c.passed or c.status == CheckStatus.WARNING for c in checks)

        return VerificationResult(
            verifier_name=self.name,
            level=self.level,
            checks=tuple(checks),
            duration_ms=duration,
            success=success,
        )

    def _check_auth_policy_exists(self, isr) -> VerificationCheck:
        auth_policies = [
            p for m in isr.system.modules for p in m.policies
            if p.policy_type == PolicyType.AUTHENTICATION
        ]
        passed = len(auth_policies) > 0
        return VerificationCheck(
            check_id="SEC-001",
            name="authentication_policy",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.CRITICAL if not passed else CheckSeverity.INFO,
            message=f"{len(auth_policies)} authentication policy(ies) defined",
            suggested_repair="" if passed else "Add an authentication policy to the ISR",
            repair_mutation_type="" if passed else "add_auth_policy",
            repair_confidence=0.0 if passed else 0.9,
        )

    def _check_authorization_defined(self, isr) -> VerificationCheck:
        all_roles: set[str] = set()
        for m in isr.system.modules:
            for p in m.policies:
                all_roles.update(p.roles)
        passed = len(all_roles) > 0
        return VerificationCheck(
            check_id="SEC-002",
            name="authorization_roles",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message=f"{len(all_roles)} role(s) defined" if passed else "No authorization roles defined",
        )

    def _check_interfaces_secured(self, isr) -> VerificationCheck:
        total_public = 0
        secured = 0
        for m in isr.system.modules:
            for iface in m.interfaces:
                if not iface.is_internal:
                    total_public += 1
                    if iface.secured_by_policy_id:
                        secured += 1

        passed = total_public == 0 or secured == total_public
        return VerificationCheck(
            check_id="SEC-003",
            name="interfaces_secured",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
            message=f"{secured}/{total_public} public interfaces secured",
            suggested_repair="" if passed else "Add secured_by_policy_id to unsecured interfaces",
            repair_mutation_type="" if passed else "add_security_binding",
            repair_confidence=0.0 if passed else 0.85,
        )

    def _check_no_hardcoded_secrets(self, ctx: VerificationContext) -> VerificationCheck:
        violations: list[str] = []
        for artifact in ctx.artifacts:
            for pattern in self.SECRET_PATTERNS:
                if pattern.search(artifact.content):
                    violations.append(artifact.path)
                    break

        passed = len(violations) == 0
        return VerificationCheck(
            check_id="SEC-004",
            name="no_hardcoded_secrets",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.CRITICAL if not passed else CheckSeverity.INFO,
            message="No hardcoded secrets detected" if passed else f"Secrets found in: {violations[:5]}",
            suggested_repair="" if passed else "Move secrets to environment variables or secrets manager",
        )

    def _check_input_validation(self, ctx: VerificationContext) -> VerificationCheck:
        source_artifacts = ctx.get_artifacts_by_type("source")
        has_validation = any(
            "valid" in a.content.lower() or "pydantic" in a.content.lower()
            or "schema" in a.content.lower()
            for a in source_artifacts
        )
        return VerificationCheck(
            check_id="SEC-005",
            name="input_validation",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if has_validation else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="Input validation detected" if has_validation else "No input validation detected",
        )
