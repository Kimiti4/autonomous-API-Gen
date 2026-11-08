"""Technology-neutral contracts for evidence-backed production diagnosis."""
from __future__ import annotations

import datetime as dt
import enum
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..services.canonical import canonical_hash


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SUPPORTED_EVENTS = {
    "http.request.completed",
    "http.request.failed",
    "service.health",
}


class EvidenceSourceKind(str, enum.Enum):
    GENERATED_SERVICE_LOG = "generated_service_log"
    METRICS_SCRAPE = "metrics_scrape"
    HEALTH_PROBE = "health_probe"


class RuntimeEvidence(BaseModel):
    """Content-addressed observation with declared, not authenticated, source identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=256)
    source_id: str = Field(min_length=1, max_length=256)
    source_kind: EvidenceSourceKind
    source_event_id: str = Field(min_length=1, max_length=256)
    schema_version: str = Field(min_length=1, max_length=32)
    event_name: str = Field(min_length=1, max_length=128)
    observed_at: dt.datetime
    payload: dict[str, Any]
    evidence_hash: str

    @field_validator("evidence_id", "source_id", "source_event_id", "schema_version", "event_name")
    @classmethod
    def _require_nonblank_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identity fields must not be blank")
        return value

    @field_validator("observed_at")
    @classmethod
    def _require_timezone(cls, value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value

    @field_validator("evidence_hash")
    @classmethod
    def _require_sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("evidence_hash must be a lowercase SHA-256 digest")
        return value

    @model_validator(mode="after")
    def _verify_provenance_hash(self) -> "RuntimeEvidence":
        if self.schema_version != "1.0":
            raise ValueError(f"unsupported evidence schema version: {self.schema_version}")
        if self.event_name not in _SUPPORTED_EVENTS:
            raise ValueError(f"unsupported runtime event: {self.event_name}")
        if self.event_name == "http.request.failed":
            error_id = self.payload.get("error_id")
            if not isinstance(error_id, str) or not error_id.strip():
                raise ValueError("http.request.failed requires a non-empty error_id")
        if self.event_name == "http.request.completed" and "status_code" in self.payload:
            status = self.payload["status_code"]
            if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
                raise ValueError("status_code must be an integer from 100 through 599")
        if self.event_name == "service.health":
            status = self.payload.get("status")
            if not isinstance(status, str) or not status.strip():
                raise ValueError("service.health requires a non-empty status")
        if canonical_hash(self.content_payload()) != self.evidence_hash:
            raise ValueError("evidence_hash does not match the evidence content")
        return self

    def content_payload(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "source_kind": self.source_kind,
            "source_event_id": self.source_event_id,
            "schema_version": self.schema_version,
            "event_name": self.event_name,
            "observed_at": self.observed_at.isoformat(),
            "payload": self.payload,
        }

    @classmethod
    def create(
        cls,
        *,
        evidence_id: str,
        source_id: str,
        source_kind: str,
        source_event_id: str,
        event_name: str,
        observed_at: dt.datetime,
        payload: dict[str, Any],
        schema_version: str = "1.0",
    ) -> "RuntimeEvidence":
        content = {
            "evidence_id": evidence_id,
            "source_id": source_id,
            "source_kind": source_kind,
            "source_event_id": source_event_id,
            "schema_version": schema_version,
            "event_name": event_name,
            "observed_at": observed_at.isoformat(),
            "payload": payload,
        }
        return cls(**content, evidence_hash=canonical_hash(content))


class FailureDetection(str, enum.Enum):
    CONFIRMED_FAILURE = "confirmed_failure"
    SUSPECTED_FAILURE = "suspected_failure"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FailureClass(str, enum.Enum):
    HTTP_SERVER_ERROR = "http_server_error"
    DECLARED_HTTP_ANOMALY = "declared_http_anomaly"
    REQUEST_PROCESSING_FAILURE = "request_processing_failure"
    SERVICE_HEALTH_FAILURE = "service_health_failure"


class DiagnosisSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class RootCauseStatus(str, enum.Enum):
    HYPOTHESIS = "hypothesis"
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"


class RecommendationExecution(str, enum.Enum):
    NOT_EXECUTED = "not_executed"


class ReviewDecision(str, enum.Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class VerificationOutcome(str, enum.Enum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


class EvidenceReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1)
    evidence_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_id: str = Field(min_length=1)
    source_event_id: str = Field(min_length=1)


class CauseHypothesis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    statement: str = Field(min_length=1)
    failure_class: FailureClass
    status: RootCauseStatus = RootCauseStatus.HYPOTHESIS
    confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Deterministic rule-match strength, not a calibrated probability or "
            "confidence in the underlying root cause."
        ),
    )
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class RemediationRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    recommendation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    action: str = Field(min_length=1)
    expected_effect: str = Field(min_length=1)
    risk: str = Field(min_length=1)
    verification_steps: tuple[str, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    execution: RecommendationExecution = RecommendationExecution.NOT_EXECUTED


class DiagnosisReview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    review_id: str = Field(min_length=1)
    recommendation_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    decision: ReviewDecision
    rationale: str = Field(min_length=1)
    verification_outcome: VerificationOutcome = VerificationOutcome.NOT_RUN
    verification_evidence_ids: tuple[str, ...] = ()
    recorded_at: dt.datetime

    @field_validator("recorded_at")
    @classmethod
    def _review_timezone(cls, value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must include a timezone")
        return value

    @model_validator(mode="after")
    def _verification_evidence_required(self) -> "DiagnosisReview":
        if (
            self.verification_outcome is not VerificationOutcome.NOT_RUN
            and not self.verification_evidence_ids
        ):
            raise ValueError("verification evidence is required when verification has run")
        if (
            self.verification_outcome is VerificationOutcome.NOT_RUN
            and self.verification_evidence_ids
        ):
            raise ValueError(
                "verification evidence is not allowed when verification has not run"
            )
        return self


class DiagnosisReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    diagnosis_id: str = Field(min_length=1)
    created_at: dt.datetime
    detection: FailureDetection
    failure_class: FailureClass | None = None
    severity: DiagnosisSeverity = DiagnosisSeverity.UNKNOWN
    confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Support for the failure classification, not probability that this "
            "hypothesis is the confirmed root cause."
        ),
    )
    evidence: tuple[EvidenceReference, ...] = ()
    hypotheses: tuple[CauseHypothesis, ...] = ()
    recommendations: tuple[RemediationRecommendation, ...] = ()
    reviews: tuple[DiagnosisReview, ...] = ()
    uncertainty_reason: str | None = None
    limitations: tuple[str, ...] = (
        "Source identities are declared by the evidence envelope, not cryptographically "
        "authenticated.",
        "Diagnosis and review records are returned in memory; durable retention is the "
        "caller's responsibility.",
        "Recommendations are proposals and are never executed by this module.",
    )

    @field_validator("created_at")
    @classmethod
    def _created_timezone(cls, value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value

    @model_validator(mode="after")
    def _validate_conclusion_evidence(self) -> "DiagnosisReport":
        evidence_ids = {item.evidence_id for item in self.evidence}
        if self.detection is FailureDetection.INSUFFICIENT_EVIDENCE:
            if self.hypotheses or self.recommendations or self.failure_class is not None:
                raise ValueError("insufficient evidence cannot assert a failure or propose a cause")
            if not self.uncertainty_reason:
                raise ValueError("insufficient evidence requires an uncertainty reason")
        if self.detection is FailureDetection.CONFLICTING_EVIDENCE:
            if self.failure_class is not None or self.hypotheses or self.recommendations:
                raise ValueError("conflicting evidence cannot assert a failure class or cause")
            if not self.uncertainty_reason:
                raise ValueError("conflicting evidence requires an uncertainty reason")
        if self.detection in {
            FailureDetection.CONFIRMED_FAILURE,
            FailureDetection.SUSPECTED_FAILURE,
            FailureDetection.CONFLICTING_EVIDENCE,
        } and not self.evidence:
            raise ValueError("failure conclusions must cite evidence")
        if self.detection in {
            FailureDetection.CONFIRMED_FAILURE,
            FailureDetection.SUSPECTED_FAILURE,
        } and self.failure_class is None:
            raise ValueError("failure classifications require a failure class")
        if self.detection in {
            FailureDetection.CONFIRMED_FAILURE,
            FailureDetection.SUSPECTED_FAILURE,
        } and (not self.hypotheses or not self.recommendations):
            raise ValueError("classified failures require hypotheses and recommendations")
        for hypothesis in self.hypotheses:
            if not set(hypothesis.evidence_ids) <= evidence_ids:
                raise ValueError("hypotheses may cite only report evidence")
            if hypothesis.status is RootCauseStatus.CONFIRMED:
                raise ValueError("automated diagnosis cannot confirm root cause")
            if hypothesis.confidence > self.confidence:
                raise ValueError("hypothesis confidence cannot exceed diagnosis confidence")
        for recommendation in self.recommendations:
            if not set(recommendation.evidence_ids) <= evidence_ids:
                raise ValueError("recommendations may cite only report evidence")
            if recommendation.execution is not RecommendationExecution.NOT_EXECUTED:
                raise ValueError("recommendations are proposals and cannot be executed")
        recommendation_ids = {item.recommendation_id for item in self.recommendations}
        for review in self.reviews:
            if review.recommendation_id not in recommendation_ids:
                raise ValueError("review must reference a recommendation in this report")
            if not set(review.verification_evidence_ids) <= evidence_ids:
                raise ValueError("verification may cite only report evidence")
            recommendation = next(
                item for item in self.recommendations
                if item.recommendation_id == review.recommendation_id
            )
            recommendation_refs = [
                item for item in self.evidence
                if item.evidence_id in recommendation.evidence_ids
            ]
            verified_refs = [
                item for item in self.evidence
                if item.evidence_id in review.verification_evidence_ids
            ]
            recommendation_source_events = {
                (item.source_id, item.source_event_id)
                for item in recommendation_refs
            }
            if any(
                verified.evidence_id in recommendation.evidence_ids
                or (verified.source_id, verified.source_event_id)
                in recommendation_source_events
                for verified in verified_refs
            ):
                raise ValueError(
                    "verification evidence must be distinct from recommendation evidence"
                )
        return self

    def with_review(self, review: DiagnosisReview) -> "DiagnosisReport":
        if any(existing.review_id == review.review_id for existing in self.reviews):
            raise ValueError("review_id must be unique within a diagnosis")
        return DiagnosisReport.model_validate(
            {**self.model_dump(), "reviews": [*self.reviews, review]}
        )
