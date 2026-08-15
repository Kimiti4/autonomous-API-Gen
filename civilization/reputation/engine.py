"""
Reputation, trust scoring, and capability certification engine.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel

from ..utils import deterministic_id, utcnow
from .models import (
    CapabilityCertification,
    CapabilityCertificationPolicy,
    CertificationApplication,
    CertificationApplicationStatus,
    CertificationStatus,
    ReputationEvent,
    ReputationEventType,
    ReputationOutcome,
    ReputationSubjectType,
    TrustPolicy,
    TrustReport,
)


class ReputationError(Exception):
    """Base error for reputation operations."""


class ReputationGovernanceDecision(BaseModel):
    """Decision returned by governance for certification operations."""

    decision: str
    reason: str = ""


class ReputationGovernanceGateway(Protocol):
    """Abstract governance gateway for reputation certification."""

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> ReputationGovernanceDecision:
        ...


class StaticReputationGovernanceGateway:
    """Static governance gateway for tests and local development."""

    def __init__(
        self,
        decision: str = "ALLOW",
        reason: str = "Static reputation governance decision.",
    ) -> None:
        self._decision = decision
        self._reason = reason

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> ReputationGovernanceDecision:
        return ReputationGovernanceDecision(
            decision=self._decision,
            reason=self._reason,
        )


def default_certification_policies() -> List[CapabilityCertificationPolicy]:
    """Return default capability certification policies."""

    return [
        CapabilityCertificationPolicy(
            capability="architecture_review",
            name="Architecture Review Certification",
            description=(
                "Certifies ability to review ISR-level architecture safely."
            ),
            required_evidence_types=[
                "isr",
                "architecture_decision",
            ],
            min_trust=0.55,
            min_completed_tasks=1,
            max_negative_events=2,
            ttl_days=180,
            required_task_types=[
                "architecture_review",
                "architecture_change",
            ],
            required_roles=[
                "software_architect",
            ],
        ),
        CapabilityCertificationPolicy(
            capability="security_review",
            name="Security Review Certification",
            description=(
                "Certifies ability to perform security review and recommend "
                "security controls."
            ),
            required_evidence_types=[
                "security_review",
            ],
            min_trust=0.60,
            min_completed_tasks=1,
            max_negative_events=1,
            ttl_days=120,
            required_task_types=[
                "security_review",
            ],
            required_roles=[
                "security_engineer",
            ],
        ),
        CapabilityCertificationPolicy(
            capability="backend_engineering",
            name="Backend Engineering Certification",
            description=(
                "Certifies backend service design and implementation review."
            ),
            required_evidence_types=[
                "service_design",
            ],
            min_trust=0.50,
            min_completed_tasks=1,
            max_negative_events=3,
            ttl_days=180,
            required_task_types=[
                "backend_design",
                "api_design",
            ],
            required_roles=[
                "backend_engineer",
            ],
        ),
        CapabilityCertificationPolicy(
            capability="database_engineering",
            name="Database Engineering Certification",
            description=(
                "Certifies persistence architecture and data integrity review."
            ),
            required_evidence_types=[
                "data_model",
            ],
            min_trust=0.50,
            min_completed_tasks=1,
            max_negative_events=3,
            ttl_days=180,
            required_task_types=[
                "database_design",
                "persistence_review",
            ],
            required_roles=[
                "database_engineer",
            ],
        ),
        CapabilityCertificationPolicy(
            capability="qa_verification",
            name="QA Verification Certification",
            description=(
                "Certifies testing strategy and verification review."
            ),
            required_evidence_types=[
                "test_strategy",
            ],
            min_trust=0.50,
            min_completed_tasks=1,
            max_negative_events=3,
            ttl_days=180,
            required_task_types=[
                "test_review",
                "quality_review",
            ],
            required_roles=[
                "qa_engineer",
            ],
        ),
        CapabilityCertificationPolicy(
            capability="documentation_engineering",
            name="Documentation Engineering Certification",
            description=(
                "Certifies documentation and traceability review."
            ),
            required_evidence_types=[
                "documentation",
            ],
            min_trust=0.45,
            min_completed_tasks=1,
            max_negative_events=3,
            ttl_days=180,
            required_task_types=[
                "documentation_review",
            ],
            required_roles=[
                "documentation_engineer",
            ],
        ),
        CapabilityCertificationPolicy(
            capability="evolution_coordination",
            name="Evolution Coordination Certification",
            description=(
                "Certifies coordination of evolution campaigns and governed "
                "architecture improvement."
            ),
            required_evidence_types=[
                "evolution_history",
            ],
            min_trust=0.60,
            min_completed_tasks=1,
            max_negative_events=1,
            ttl_days=120,
            required_task_types=[
                "evolution_campaign",
            ],
            required_roles=[
                "evolution_coordinator",
            ],
        ),
    ]


class ReputationEngine:
    """Engine for reputation events, trust scoring, and certification."""

    def __init__(
        self,
        trust_policy: Optional[TrustPolicy] = None,
        certification_policies: Optional[
            List[CapabilityCertificationPolicy]
        ] = None,
        governance_gateway: Optional[ReputationGovernanceGateway] = None,
    ) -> None:
        self.trust_policy = trust_policy or TrustPolicy()

        policies = certification_policies or default_certification_policies()

        self.certification_policies: Dict[str, CapabilityCertificationPolicy] = {
            policy.capability: policy
            for policy in policies
        }

        self.governance = governance_gateway or StaticReputationGovernanceGateway()

        self.events: List[ReputationEvent] = []
        self.events_by_subject: Dict[str, List[ReputationEvent]] = {}

        self.applications: Dict[str, CertificationApplication] = {}
        self.certifications: Dict[str, CapabilityCertification] = {}

    # ------------------------------------------------------------------
    # Reputation events
    # ------------------------------------------------------------------

    def record_event(
        self,
        subject_type: ReputationSubjectType,
        subject_id: str,
        event_type: ReputationEventType,
        outcome: ReputationOutcome,
        weight: Optional[float] = None,
        capability: Optional[str] = None,
        task_id: Optional[str] = None,
        initiative_id: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        created_at: Optional[str] = None,
    ) -> ReputationEvent:
        if weight is None:
            weight = 0.1

        weight = min(
            max(0.0, weight),
            self.trust_policy.max_event_weight,
        )

        timestamp = created_at or utcnow().isoformat()

        event_id = deterministic_id(
            "reputation_event",
            {
                "subject_type": subject_type.value,
                "subject_id": subject_id,
                "event_type": event_type.value,
                "outcome": outcome.value,
                "task_id": task_id,
                "initiative_id": initiative_id,
                "capability": capability,
                "created_at": timestamp,
                "event_count": len(self.events),
            },
        )

        event = ReputationEvent(
            id=event_id,
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
            outcome=outcome,
            weight=weight,
            capability=capability,
            task_id=task_id,
            initiative_id=initiative_id,
            evidence_refs=evidence_refs or [],
            metadata=metadata or {},
            created_at=timestamp,
        )

        self.events.append(event)

        subject_key = self._subject_key(subject_type, subject_id)

        self.events_by_subject.setdefault(subject_key, []).append(event)

        return event

    def record_task_outcome(
        self,
        subject_type: ReputationSubjectType,
        subject_id: str,
        task_id: str,
        outcome: ReputationOutcome,
        capability: Optional[str] = None,
        task_type: Optional[str] = None,
        weight: Optional[float] = None,
        evidence_refs: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> ReputationEvent:
        event_metadata = dict(metadata or {})

        if task_type:
            event_metadata["task_type"] = task_type

        return self.record_event(
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=ReputationEventType.TASK_OUTCOME,
            outcome=outcome,
            weight=weight,
            capability=capability,
            task_id=task_id,
            evidence_refs=evidence_refs,
            metadata=event_metadata,
        )

    def list_events(
        self,
        subject_type: Optional[ReputationSubjectType] = None,
        subject_id: Optional[str] = None,
        event_type: Optional[ReputationEventType] = None,
        limit: int = 100,
    ) -> List[ReputationEvent]:
        results: List[ReputationEvent] = []

        for event in reversed(self.events):
            if subject_type and event.subject_type != subject_type:
                continue

            if subject_id and event.subject_id != subject_id:
                continue

            if event_type and event.event_type != event_type:
                continue

            results.append(event)

            if len(results) >= limit:
                break

        return results

    # ------------------------------------------------------------------
    # Trust scoring
    # ------------------------------------------------------------------

    def trust_report(
        self,
        subject_type: ReputationSubjectType,
        subject_id: str,
        now: Optional[datetime] = None,
    ) -> TrustReport:
        current_time = now or utcnow()

        subject_key = self._subject_key(subject_type, subject_id)

        events = self.events_by_subject.get(subject_key, [])

        positive_effect = 0.0
        negative_effect = 0.0

        raw_effect = 0.0
        weighted_event_count = 0.0

        recent_positive_count = 0
        recent_negative_count = 0

        recent_window = timedelta(days=30)

        for event in events:
            event_time = self._parse_timestamp(event.created_at)

            age_days = max(
                0.0,
                (current_time - event_time).total_seconds() / 86400.0,
            )

            decay = math.exp(
                -age_days * math.log(2) / self.trust_policy.half_life_days
            )

            weighted_event_count += decay

            if event.outcome == ReputationOutcome.POSITIVE:
                effect = event.weight
                positive_effect += effect * decay

                if current_time - event_time <= recent_window:
                    recent_positive_count += 1

            elif event.outcome == ReputationOutcome.NEGATIVE:
                effect = -event.weight
                negative_effect += abs(effect) * decay

                if current_time - event_time <= recent_window:
                    recent_negative_count += 1

            else:
                effect = 0.0

            raw_effect += effect * decay

        normalized_effect = raw_effect / self.trust_policy.normalization_factor

        score = self.trust_policy.initial_trust + normalized_effect

        score = min(
            max(score, self.trust_policy.min_trust),
            self.trust_policy.max_trust,
        )

        confidence = min(
            1.0,
            weighted_event_count / self.trust_policy.confidence_event_target,
        )

        factors = {
            "raw_effect": round(raw_effect, 6),
            "normalized_effect": round(normalized_effect, 6),
            "positive_effect": round(positive_effect, 6),
            "negative_effect": round(negative_effect, 6),
            "weighted_event_count": round(weighted_event_count, 6),
            "half_life_days": self.trust_policy.half_life_days,
            "initial_trust": self.trust_policy.initial_trust,
        }

        return TrustReport(
            subject_type=subject_type,
            subject_id=subject_id,
            score=round(score, 6),
            confidence=round(confidence, 6),
            positive_effect=round(positive_effect, 6),
            negative_effect=round(negative_effect, 6),
            event_count=len(events),
            recent_positive_count=recent_positive_count,
            recent_negative_count=recent_negative_count,
            factors=factors,
            updated_at=current_time.isoformat(),
        )

    # ------------------------------------------------------------------
    # Certification
    # ------------------------------------------------------------------

    def apply_certification(
        self,
        subject_type: ReputationSubjectType,
        subject_id: str,
        capability: str,
        evidence_refs: List[str],
        actor_id: str = "reputation_api",
    ) -> tuple[CertificationApplication, Optional[CapabilityCertification]]:
        policy = self.certification_policies.get(capability)

        if not policy:
            raise ReputationError(
                f"No certification policy found for capability: {capability}"
            )

        created_at = utcnow().isoformat()

        application_id = deterministic_id(
            "certification_application",
            {
                "subject_type": subject_type.value,
                "subject_id": subject_id,
                "capability": capability,
                "created_at": created_at,
                "application_count": len(self.applications),
            },
        )

        application = CertificationApplication(
            id=application_id,
            subject_type=subject_type,
            subject_id=subject_id,
            capability=capability,
            evidence_refs=evidence_refs,
            status=CertificationApplicationStatus.PENDING,
            created_at=created_at,
        )

        self.applications[application_id] = application

        if policy.require_governance:
            governance_decision = self.governance.evaluate_action(
                action="CERTIFY_CAPABILITY",
                context={
                    "subject_type": subject_type.value,
                    "subject_id": subject_id,
                    "capability": capability,
                    "actor_id": actor_id,
                },
            )

            if governance_decision.decision != "ALLOW":
                application.status = CertificationApplicationStatus.REJECTED
                application.reason = governance_decision.reason
                application.decided_at = utcnow().isoformat()

                return application, None

        trust = self.trust_report(subject_type, subject_id)

        completed_tasks = self._completed_task_count(
            subject_type=subject_type,
            subject_id=subject_id,
            policy=policy,
        )

        negative_events = self._negative_event_count(
            subject_type=subject_type,
            subject_id=subject_id,
        )

        evidence_satisfied = self._evidence_satisfied(
            required_evidence_types=policy.required_evidence_types,
            evidence_refs=evidence_refs,
        )

        reasons: List[str] = []

        if trust.score < policy.min_trust:
            reasons.append(
                f"Trust score {trust.score:.3f} below required "
                f"{policy.min_trust:.3f}."
            )

        if completed_tasks < policy.min_completed_tasks:
            reasons.append(
                f"Completed task count {completed_tasks} below required "
                f"{policy.min_completed_tasks}."
            )

        if negative_events > policy.max_negative_events:
            reasons.append(
                f"Negative event count {negative_events} exceeds maximum "
                f"{policy.max_negative_events}."
            )

        if not evidence_satisfied:
            reasons.append(
                "Evidence does not satisfy required evidence types: "
                + ", ".join(policy.required_evidence_types)
            )

        if reasons:
            application.status = CertificationApplicationStatus.REJECTED
            application.reason = " ".join(reasons)
            application.decided_at = utcnow().isoformat()

            return application, None

        issued_at = utcnow()
        expires_at = issued_at + timedelta(days=policy.ttl_days)

        certification_id = deterministic_id(
            "capability_certification",
            {
                "application_id": application_id,
                "subject_type": subject_type.value,
                "subject_id": subject_id,
                "capability": capability,
                "issued_at": issued_at.isoformat(),
            },
        )

        certification = CapabilityCertification(
            id=certification_id,
            application_id=application_id,
            subject_type=subject_type,
            subject_id=subject_id,
            capability=capability,
            level="certified",
            status=CertificationStatus.ACTIVE,
            evidence_refs=evidence_refs,
            issued_at=issued_at.isoformat(),
            expires_at=expires_at.isoformat(),
            issuer=actor_id,
            rationale="Certification requirements satisfied.",
        )

        self.certifications[certification_id] = certification

        application.status = CertificationApplicationStatus.APPROVED
        application.reason = "Certification requirements satisfied."
        application.decided_at = utcnow().isoformat()

        return application, certification

    def list_certifications(
        self,
        subject_type: Optional[ReputationSubjectType] = None,
        subject_id: Optional[str] = None,
        capability: Optional[str] = None,
        active_only: bool = True,
        now: Optional[datetime] = None,
    ) -> List[CapabilityCertification]:
        self.check_expirations(now=now)

        results: List[CapabilityCertification] = []

        for certification in self.certifications.values():
            if subject_type and certification.subject_type != subject_type:
                continue

            if subject_id and certification.subject_id != subject_id:
                continue

            if capability and certification.capability != capability:
                continue

            if active_only and certification.status != CertificationStatus.ACTIVE:
                continue

            results.append(certification)

        return results

    def revoke_certification(
        self,
        certification_id: str,
        reason: str,
        actor_id: str = "reputation_api",
    ) -> CapabilityCertification:
        certification = self.certifications.get(certification_id)

        if not certification:
            raise ReputationError(
                f"Certification not found: {certification_id}"
            )

        certification.status = CertificationStatus.REVOKED
        certification.revoked_at = utcnow().isoformat()
        certification.revocation_reason = reason
        certification.issuer = actor_id

        return certification

    def check_expirations(
        self,
        now: Optional[datetime] = None,
    ) -> List[str]:
        current_time = now or utcnow()

        expired_ids: List[str] = []

        for certification in self.certifications.values():
            if certification.status != CertificationStatus.ACTIVE:
                continue

            expires_at = self._parse_timestamp(certification.expires_at)

            if expires_at <= current_time:
                certification.status = CertificationStatus.EXPIRED
                expired_ids.append(certification.id)

        return expired_ids

    def can_perform(
        self,
        subject_type: ReputationSubjectType,
        subject_id: str,
        capability: str,
        now: Optional[datetime] = None,
    ) -> bool:
        policy = self.certification_policies.get(capability)

        if not policy:
            return False

        certifications = self.list_certifications(
            subject_type=subject_type,
            subject_id=subject_id,
            capability=capability,
            active_only=True,
            now=now,
        )

        if not certifications:
            return False

        trust = self.trust_report(subject_type, subject_id, now=now)

        return trust.score >= policy.min_trust

    def capability_report(
        self,
        subject_type: ReputationSubjectType,
        subject_id: str,
        capability: str,
        now: Optional[datetime] = None,
    ) -> Dict:
        policy = self.certification_policies.get(capability)

        if not policy:
            raise ReputationError(
                f"No certification policy found for capability: {capability}"
            )

        trust = self.trust_report(subject_type, subject_id, now=now)

        certifications = self.list_certifications(
            subject_type=subject_type,
            subject_id=subject_id,
            capability=capability,
            active_only=False,
            now=now,
        )

        completed_tasks = self._completed_task_count(
            subject_type=subject_type,
            subject_id=subject_id,
            policy=policy,
        )

        negative_events = self._negative_event_count(
            subject_type=subject_type,
            subject_id=subject_id,
        )

        active_certification = next(
            (
                certification
                for certification in certifications
                if certification.status == CertificationStatus.ACTIVE
            ),
            None,
        )

        return {
            "policy": policy,
            "trust": trust,
            "certifications": certifications,
            "active_certification": active_certification,
            "completed_task_count": completed_tasks,
            "negative_event_count": negative_events,
            "authorized": self.can_perform(
                subject_type=subject_type,
                subject_id=subject_id,
                capability=capability,
                now=now,
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _subject_key(
        self,
        subject_type: ReputationSubjectType,
        subject_id: str,
    ) -> str:
        return f"{subject_type.value}:{subject_id}"

    def _parse_timestamp(self, value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return utcnow()

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed

    def _completed_task_count(
        self,
        subject_type: ReputationSubjectType,
        subject_id: str,
        policy: CapabilityCertificationPolicy,
    ) -> int:
        subject_key = self._subject_key(subject_type, subject_id)

        events = self.events_by_subject.get(subject_key, [])

        task_ids: set[str] = set()

        for event in events:
            if event.event_type != ReputationEventType.TASK_OUTCOME:
                continue

            if event.outcome != ReputationOutcome.POSITIVE:
                continue

            if not event.task_id:
                continue

            if policy.required_task_types:
                task_type = event.metadata.get("task_type")

                if task_type not in policy.required_task_types:
                    continue

            if policy.capability and event.capability:
                if event.capability != policy.capability:
                    continue

            task_ids.add(event.task_id)

        return len(task_ids)

    def _negative_event_count(
        self,
        subject_type: ReputationSubjectType,
        subject_id: str,
    ) -> int:
        subject_key = self._subject_key(subject_type, subject_id)

        events = self.events_by_subject.get(subject_key, [])

        return sum(
            1
            for event in events
            if event.outcome == ReputationOutcome.NEGATIVE
        )

    def _evidence_satisfied(
        self,
        required_evidence_types: List[str],
        evidence_refs: List[str],
    ) -> bool:
        if not required_evidence_types:
            return True

        normalized_evidence = [
            evidence.lower()
            for evidence in evidence_refs
        ]

        for required_type in required_evidence_types:
            required = required_type.lower()

            satisfied = any(
                required in evidence
                for evidence in normalized_evidence
            )

            if not satisfied:
                return False

        return True
