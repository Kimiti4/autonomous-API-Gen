"""
Compiler production gate.

This enforcer evaluates whether a compilation request is allowed to proceed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..errors import BackendNotFoundError
from ..models import CompilationRequest, utcnow
from ..registry import BackendRegistry
from ..sdk.models import CertificationStatus
from .audit import AuditEmitter, CompilerAuditEvent, LoggingAuditEmitter
from .client import GovernanceClient
from .models import (
    CompilationGateDecision,
    CompilerGovernancePolicy,
    GovernanceDecision,
    GovernanceEvaluationRequest,
)


class CompilerGovernanceEnforcer:
    """Evaluates compilation requests against governance policy."""

    def __init__(
        self,
        registry: BackendRegistry,
        certification_engine,
        governance_client: Optional[GovernanceClient] = None,
        policy: Optional[CompilerGovernancePolicy] = None,
        audit_emitter: Optional[AuditEmitter] = None,
    ) -> None:
        self.registry = registry
        self.certification_engine = certification_engine
        self.governance_client = governance_client
        self.policy = policy or CompilerGovernancePolicy()
        self.audit_emitter = audit_emitter or LoggingAuditEmitter()

    def evaluate_compilation(
        self,
        request: CompilationRequest,
    ) -> CompilationGateDecision:
        """Evaluate whether compilation is allowed."""

        environment = (request.environment or "development").lower()

        try:
            manifest = self.registry.get_manifest(
                request.target.backend_id,
                request.target.backend_version,
            )
        except BackendNotFoundError as exc:
            return self._deny(
                reason=str(exc),
                environment=environment,
                backend_id=request.target.backend_id,
                backend_version=request.target.backend_version or "unknown",
                actor_id=request.actor_id or "anonymous",
            )

        certification = None

        if self.certification_engine:
            certification = self.certification_engine.get_report(
                manifest.backend_id,
                manifest.version,
            )

        certification_status = (
            certification.status.value
            if certification
            else CertificationStatus.UNCERTIFIED.value
        )

        production_environments = {
            item.lower()
            for item in self.policy.production_environments
        }

        certified_required_environments = {
            item.lower()
            for item in self.policy.certified_required_environments
        }

        is_production = environment in production_environments
        certification_required = (
            environment in certified_required_environments
            or is_production
        )

        # --------------------------------------------------------------
        # Production gating
        # --------------------------------------------------------------

        if is_production:
            if certification is None:
                return self._deny(
                    reason=(
                        "Production compilation requires a certified backend."
                    ),
                    environment=environment,
                    backend_id=manifest.backend_id,
                    backend_version=manifest.version,
                    actor_id=request.actor_id or "anonymous",
                    certification_status=certification_status,
                )

            if certification.status != CertificationStatus.CERTIFIED:
                return self._deny(
                    reason=(
                        "Production compilation requires CERTIFIED backend "
                        "status."
                    ),
                    environment=environment,
                    backend_id=manifest.backend_id,
                    backend_version=manifest.version,
                    actor_id=request.actor_id or "anonymous",
                    certification_status=certification_status,
                )

            if self._certification_expired(certification):
                return self._deny(
                    reason="Backend certification has expired.",
                    environment=environment,
                    backend_id=manifest.backend_id,
                    backend_version=manifest.version,
                    actor_id=request.actor_id or "anonymous",
                    certification_status=certification_status,
                )

            if self.policy.require_governance_for_production:
                governance_decision = self._evaluate_governance(
                    request=request,
                    manifest=manifest,
                    environment=environment,
                    certification_status=certification_status,
                )

                if governance_decision.decision not in {
                    "ALLOW",
                    "ALLOW_WITH_CONSTRAINTS",
                }:
                    return self._deny(
                        reason=(
                            "Governance denied production compilation: "
                            f"{governance_decision.reason}"
                        ),
                        environment=environment,
                        backend_id=manifest.backend_id,
                        backend_version=manifest.version,
                        actor_id=request.actor_id or "anonymous",
                        certification_status=certification_status,
                        governance_decision=governance_decision,
                    )

                return self._allow(
                    reason="Production compilation allowed by governance.",
                    environment=environment,
                    backend_id=manifest.backend_id,
                    backend_version=manifest.version,
                    actor_id=request.actor_id or "anonymous",
                    certification_status=certification_status,
                    governance_decision=governance_decision,
                    constraints=governance_decision.constraints,
                )

            return self._allow(
                reason=(
                    "Production compilation allowed by certification policy."
                ),
                environment=environment,
                backend_id=manifest.backend_id,
                backend_version=manifest.version,
                actor_id=request.actor_id or "anonymous",
                certification_status=certification_status,
            )

        # --------------------------------------------------------------
        # Protected non-production environments
        # --------------------------------------------------------------

        if certification_required:
            if certification is None:
                return self._deny(
                    reason=(
                        "This environment requires a certified backend."
                    ),
                    environment=environment,
                    backend_id=manifest.backend_id,
                    backend_version=manifest.version,
                    actor_id=request.actor_id or "anonymous",
                    certification_status=certification_status,
                )

            allowed_statuses = {CertificationStatus.CERTIFIED}

            if self.policy.allow_provisional_in_non_production:
                allowed_statuses.add(CertificationStatus.PROVISIONAL)

            if certification.status not in allowed_statuses:
                return self._deny(
                    reason=(
                        "This environment requires CERTIFIED or PROVISIONAL "
                        "backend status."
                    ),
                    environment=environment,
                    backend_id=manifest.backend_id,
                    backend_version=manifest.version,
                    actor_id=request.actor_id or "anonymous",
                    certification_status=certification_status,
                )

            return self._allow(
                reason="Compilation allowed for protected environment.",
                environment=environment,
                backend_id=manifest.backend_id,
                backend_version=manifest.version,
                actor_id=request.actor_id or "anonymous",
                certification_status=certification_status,
            )

        # --------------------------------------------------------------
        # Development environments
        # --------------------------------------------------------------

        if not self.policy.allow_uncertified_development:
            if certification is None:
                return self._deny(
                    reason=(
                        "Development compilation requires at least a "
                        "provisional certification under current policy."
                    ),
                    environment=environment,
                    backend_id=manifest.backend_id,
                    backend_version=manifest.version,
                    actor_id=request.actor_id or "anonymous",
                    certification_status=certification_status,
                )

            allowed_statuses = {
                CertificationStatus.CERTIFIED,
                CertificationStatus.PROVISIONAL,
            }

            if certification.status not in allowed_statuses:
                return self._deny(
                    reason=(
                        "Development compilation requires CERTIFIED or "
                        "PROVISIONAL backend status under current policy."
                    ),
                    environment=environment,
                    backend_id=manifest.backend_id,
                    backend_version=manifest.version,
                    actor_id=request.actor_id or "anonymous",
                    certification_status=certification_status,
                )

        return self._allow(
            reason="Development compilation allowed by policy.",
            environment=environment,
            backend_id=manifest.backend_id,
            backend_version=manifest.version,
            actor_id=request.actor_id or "anonymous",
            certification_status=certification_status,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evaluate_governance(
        self,
        request: CompilationRequest,
        manifest,
        environment: str,
        certification_status: str,
    ) -> GovernanceDecision:
        if not self.governance_client:
            if self.policy.fail_closed_on_governance_unavailable:
                return GovernanceDecision(
                    decision="DENY",
                    reason=(
                        "Governance client is unavailable and policy "
                        "requires fail-closed behavior."
                    ),
                )

            return GovernanceDecision(
                decision="ALLOW",
                reason=(
                    "Governance client is unavailable but policy allows "
                    "fallback."
                ),
            )

        governance_request = GovernanceEvaluationRequest(
            subject_type="COMPILER_BACKEND",
            subject_id=f"{manifest.backend_id}@{manifest.version}",
            action="COMPILE_ISR",
            actor={
                "actor_type": "HUMAN" if request.actor_id else "SERVICE",
                "actor_id": request.actor_id or "compiler",
                "roles": [],
                "delegated_authority": [],
            },
            context={
                "environment": environment,
                "backend_id": manifest.backend_id,
                "backend_version": manifest.version,
                "certification_status": certification_status,
                "isr_id": request.isr.get("isr_id"),
                "isr_version": request.isr.get("version"),
            },
            evidence_refs=[
                f"certification:{manifest.backend_id}@{manifest.version}",
            ],
        )

        return self.governance_client.evaluate(governance_request)

    def _certification_expired(self, certification) -> bool:
        if self.policy.max_certification_age_days is None:
            return False

        if certification.status != CertificationStatus.CERTIFIED:
            return False

        certified_at = certification.certified_at

        if not certified_at:
            return True

        try:
            parsed = datetime.fromisoformat(
                certified_at.replace("Z", "+00:00")
            )
        except ValueError:
            return True

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        age_days = (utcnow() - parsed).days

        return age_days > self.policy.max_certification_age_days

    def _allow(
        self,
        reason: str,
        environment: str,
        backend_id: str,
        backend_version: str,
        actor_id: str,
        certification_status: Optional[str] = None,
        governance_decision: Optional[GovernanceDecision] = None,
        constraints: Optional[list[dict]] = None,
    ) -> CompilationGateDecision:
        decision = CompilationGateDecision(
            allowed=True,
            reason=reason,
            environment=environment,
            backend_id=backend_id,
            backend_version=backend_version,
            certification_status=certification_status,
            governance_decision=governance_decision,
            constraints=constraints or [],
        )

        self.audit_emitter.emit(
            CompilerAuditEvent(
                event_type="compilation_allowed",
                backend_id=backend_id,
                backend_version=backend_version,
                environment=environment,
                actor_id=actor_id,
                reason=reason,
                details=decision.model_dump(mode="json"),
            )
        )

        return decision

    def _deny(
        self,
        reason: str,
        environment: str,
        backend_id: str,
        backend_version: str,
        actor_id: str,
        certification_status: Optional[str] = None,
        governance_decision: Optional[GovernanceDecision] = None,
    ) -> CompilationGateDecision:
        decision = CompilationGateDecision(
            allowed=False,
            reason=reason,
            environment=environment,
            backend_id=backend_id,
            backend_version=backend_version,
            certification_status=certification_status,
            governance_decision=governance_decision,
        )

        self.audit_emitter.emit(
            CompilerAuditEvent(
                event_type="compilation_denied",
                backend_id=backend_id,
                backend_version=backend_version,
                environment=environment,
                actor_id=actor_id,
                reason=reason,
                details=decision.model_dump(mode="json"),
            )
        )

        return decision
