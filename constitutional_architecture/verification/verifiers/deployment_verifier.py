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


class DeploymentVerifier(Verifier):
    @property
    def name(self) -> str:
        return "deployment"

    @property
    def description(self) -> str:
        return "Verify deployment configuration completeness"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L5_OPERATIONAL

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []
        isr = ctx.isr

        has_deployment = isr.system.deployment is not None
        checks.append(VerificationCheck(
            check_id="DEPLOY-001",
            name="deployment_defined",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if has_deployment else CheckStatus.FAILED,
            severity=CheckSeverity.ERROR if not has_deployment else CheckSeverity.INFO,
            message="Deployment configuration defined" if has_deployment else "No deployment configuration",
            suggested_repair="" if has_deployment else "Add deployment configuration to ISR",
            repair_mutation_type="" if has_deployment else "add_deployment",
        ))

        if ctx.has_artifacts:
            docker_files = [a for a in ctx.artifacts if "docker" in a.path.lower()]
            checks.append(VerificationCheck(
                check_id="DEPLOY-002",
                name="container_config",
                verifier=self.name,
                level=self.level,
                status=CheckStatus.PASSED if docker_files else CheckStatus.WARNING,
                severity=CheckSeverity.WARNING,
                message=f"{len(docker_files)} container config(s) found",
            ))

        if has_deployment and isr.system.deployment:
            monitoring = isr.system.deployment.monitoring
            has_health = bool(monitoring and monitoring.health_check_path)
            checks.append(VerificationCheck(
                check_id="DEPLOY-003",
                name="health_checks",
                verifier=self.name,
                level=self.level,
                status=CheckStatus.PASSED if has_health else CheckStatus.WARNING,
                severity=CheckSeverity.WARNING,
                message="Health check configured" if has_health else "No health check path",
            ))

        duration = (time.perf_counter() - start) * 1000
        success = all(c.passed or c.status == CheckStatus.WARNING for c in checks)
        return VerificationResult(
            verifier_name=self.name, level=self.level,
            checks=tuple(checks), duration_ms=duration, success=success,
        )
