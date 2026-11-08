"""Deterministic, non-executing diagnosis over source-bound runtime evidence."""
from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence

from pydantic import ValidationError

from tiannara.domain.models.diagnosis import (
    CauseHypothesis,
    DiagnosisReport,
    DiagnosisReview,
    DiagnosisSeverity,
    EvidenceReference,
    FailureClass,
    FailureDetection,
    RemediationRecommendation,
    ReviewDecision,
    RootCauseStatus,
    RuntimeEvidence,
    VerificationOutcome,
)


class EvidenceIngestionError(ValueError):
    """Evidence is malformed, untraceable, unsupported, or contradictory."""


class DiagnosisInputError(ValueError):
    """A requested review does not match the diagnosis record."""


class RuntimeDiagnosis:
    """Analyze CAP-013 runtime evidence without performing production actions."""

    def __init__(
        self,
        *,
        server_error_threshold: int = 500,
        suspected_status_codes: tuple[int, ...] = (),
    ) -> None:
        if not 500 <= server_error_threshold <= 599:
            raise ValueError("server_error_threshold must be between 500 and 599")
        if any(
            isinstance(code, bool)
            or not isinstance(code, int)
            or not 100 <= code < server_error_threshold
            for code in suspected_status_codes
        ):
            raise ValueError(
                "suspected_status_codes must be HTTP status codes below server_error_threshold"
            )
        self._server_error_threshold = server_error_threshold
        self._suspected_status_codes = frozenset(suspected_status_codes)

    def ingest(self, records: Sequence[RuntimeEvidence]) -> tuple[RuntimeEvidence, ...]:
        unique: dict[str, RuntimeEvidence] = {}
        source_events: dict[tuple[str, str], RuntimeEvidence] = {}
        for supplied in records:
            if not isinstance(supplied, RuntimeEvidence):
                raise EvidenceIngestionError("evidence must be validated RuntimeEvidence records")
            try:
                record = RuntimeEvidence.model_validate(supplied.model_dump())
            except ValidationError as exc:
                raise EvidenceIngestionError(
                    f"evidence {supplied.evidence_id!r} failed integrity validation"
                ) from exc
            prior = unique.get(record.evidence_id)
            if prior is not None:
                if prior.evidence_hash != record.evidence_hash:
                    raise EvidenceIngestionError(
                        f"evidence_id {record.evidence_id!r} has conflicting content"
                    )
                continue
            source_key = (record.source_id, record.source_event_id)
            prior_source = source_events.get(source_key)
            if prior_source is not None and prior_source.evidence_hash != record.evidence_hash:
                raise EvidenceIngestionError(
                    "source event identity is reused with conflicting evidence"
                )
            unique[record.evidence_id] = record
            source_events[source_key] = record
        return tuple(sorted(unique.values(), key=lambda item: (
            item.observed_at, item.source_id, item.source_event_id, item.evidence_id
        )))

    def diagnose(self, records: Sequence[RuntimeEvidence]) -> DiagnosisReport:
        evidence = self.ingest(records)
        references = tuple(self._reference(item) for item in evidence)
        if not evidence:
            return self._insufficient(references, "No runtime evidence was supplied.")

        signals = [self._signal(item) for item in evidence]
        signals = [signal for signal in signals if signal is not None]
        if not signals:
            return self._insufficient(
                references,
                "Evidence contains no supported, sufficiently complete failure signal.",
            )

        conflict_ids = self._conflicts(signals)
        if conflict_ids:
            return DiagnosisReport(
                diagnosis_id=str(uuid.uuid4()),
                created_at=dt.datetime.now(dt.UTC),
                detection=FailureDetection.CONFLICTING_EVIDENCE,
                confidence=0.0,
                evidence=references,
                uncertainty_reason=(
                    "Evidence for the same request identity contains incompatible outcomes; "
                    "no failure class or root cause is asserted."
                ),
            )

        failures = [signal for signal in signals if signal[1] is not None]
        if not failures:
            return self._insufficient(
                references,
                "Observed signals do not meet the declared failure rules.",
            )

        classified = self._resolve_failure_signals(failures)
        failure_classes = {signal[1] for signal in classified}
        if len(failure_classes) != 1:
            return DiagnosisReport(
                diagnosis_id=str(uuid.uuid4()),
                created_at=dt.datetime.now(dt.UTC),
                detection=FailureDetection.CONFLICTING_EVIDENCE,
                confidence=0.0,
                evidence=references,
                uncertainty_reason=(
                    "Evidence indicates multiple incompatible failure classes; "
                    "no single diagnosis is selected."
                ),
            )

        failure_class = next(iter(failure_classes))
        related = [signal[0] for signal in classified]
        ids = tuple(item.evidence_id for item in related)
        suspected = failure_class is FailureClass.DECLARED_HTTP_ANOMALY
        confidence = (
            0.55
            if suspected
            else 0.95
            if any(item.event_name == "http.request.failed" for item in related)
            else 0.90
        )
        detection = (
            FailureDetection.SUSPECTED_FAILURE
            if suspected
            else FailureDetection.CONFIRMED_FAILURE
        )
        hypothesis = CauseHypothesis(
            statement=(
                f"Runtime evidence indicates {failure_class.value}, but does not establish "
                "its underlying root cause."
            ),
            failure_class=failure_class,
            status=RootCauseStatus.HYPOTHESIS,
            confidence=confidence,
            evidence_ids=ids,
            rationale=(
                "The classification follows an explicit runtime failure event or the "
                f"configured HTTP status threshold ({self._server_error_threshold}+). "
                "No causal dependency evidence is available in this gate."
            ),
        )
        recommendation = self._recommendation(failure_class, ids, suspected=suspected)
        return DiagnosisReport(
            diagnosis_id=str(uuid.uuid4()),
            created_at=dt.datetime.now(dt.UTC),
            detection=detection,
            failure_class=failure_class,
            severity=DiagnosisSeverity.MEDIUM if suspected else DiagnosisSeverity.HIGH,
            confidence=confidence,
            evidence=references,
            hypotheses=(hypothesis,),
            recommendations=(recommendation,),
        )

    def review(
        self,
        report: DiagnosisReport,
        *,
        recommendation_id: str,
        reviewer_id: str,
        decision: ReviewDecision,
        rationale: str,
        verification_outcome: VerificationOutcome = VerificationOutcome.NOT_RUN,
        verification_evidence: Sequence[RuntimeEvidence] = (),
    ) -> DiagnosisReport:
        recommendation_ids = {
            item.recommendation_id for item in report.recommendations
        }
        if recommendation_id not in recommendation_ids:
            raise DiagnosisInputError("review references an unknown recommendation")
        try:
            verified = self.ingest(verification_evidence)
            known_refs = {item.evidence_id: item for item in report.evidence}
            recommendation = next(
                item for item in report.recommendations
                if item.recommendation_id == recommendation_id
            )
            recommendation_refs = {
                item.evidence_id: item
                for item in report.evidence
                if item.evidence_id in recommendation.evidence_ids
            }
            recommendation_source_events = {
                (item.source_id, item.source_event_id)
                for item in recommendation_refs.values()
            }
            for record in verified:
                reference = self._reference(record)
                if (
                    reference.evidence_id in recommendation_refs
                    or (reference.source_id, reference.source_event_id)
                    in recommendation_source_events
                ):
                    raise DiagnosisInputError(
                        "verification evidence must be distinct from recommendation evidence"
                    )
                existing = known_refs.get(reference.evidence_id)
                if existing is not None and existing != reference:
                    raise EvidenceIngestionError(
                        f"verification evidence {reference.evidence_id!r} "
                        "conflicts with report evidence"
                    )
                known_refs[reference.evidence_id] = reference
            review = DiagnosisReview(
                review_id=str(uuid.uuid4()),
                recommendation_id=recommendation_id,
                reviewer_id=reviewer_id,
                decision=decision,
                rationale=rationale,
                verification_outcome=verification_outcome,
                verification_evidence_ids=tuple(item.evidence_id for item in verified),
                recorded_at=dt.datetime.now(dt.UTC),
            )
            return DiagnosisReport.model_validate(
                {
                    **report.model_dump(),
                    "evidence": list(known_refs.values()),
                    "reviews": [*report.reviews, review],
                }
            )
        except ValidationError as exc:
            raise DiagnosisInputError(str(exc)) from exc

    def _signal(
        self, record: RuntimeEvidence
    ) -> tuple[RuntimeEvidence, FailureClass | None, int | None, tuple[str, ...]] | None:
        payload = record.payload
        if record.event_name == "http.request.failed":
            error_id = payload.get("error_id")
            if not isinstance(error_id, str) or not error_id.strip():
                return None
            return record, FailureClass.REQUEST_PROCESSING_FAILURE, 500, self._identities(payload)

        if record.event_name == "http.request.completed":
            status = payload.get("status_code")
            if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
                return None
            failure_class = (
                FailureClass.HTTP_SERVER_ERROR
                if status >= self._server_error_threshold
                else FailureClass.DECLARED_HTTP_ANOMALY
                if status in self._suspected_status_codes
                else None
            )
            return record, failure_class, status, self._identities(payload)

        status_value = payload.get("status")
        if not isinstance(status_value, str):
            return None
        status = status_value.strip().lower()
        if status in {"failed", "unhealthy", "down"}:
            return record, FailureClass.SERVICE_HEALTH_FAILURE, None, self._identities(payload)
        if status in {"healthy", "ready", "alive"}:
            return record, None, None, self._identities(payload)
        return None

    @staticmethod
    def _identities(payload: dict) -> tuple[str, ...]:
        identities = []
        for key in ("request_id", "correlation_id", "trace_id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                identities.append(f"{key}:{value}")
        return tuple(identities)

    @staticmethod
    def _conflicts(signals: list[tuple]) -> set[str]:
        conflicting_ids: set[str] = set()
        for group in RuntimeDiagnosis._incident_groups(signals):
            has_failure = any(item[1] is not None for item in group)
            has_success = any(
                (
                    item[2] is not None
                    and item[1] is None
                    and item[2] < 500
                )
                or (
                    item[0].event_name == "service.health"
                    and item[0].payload.get("status", "").lower() in {"healthy", "ready", "alive"}
                )
                for item in group
            )
            if has_failure and has_success:
                conflicting_ids.update(item[0].evidence_id for item in group)
        return conflicting_ids

    @staticmethod
    def _resolve_failure_signals(failures: list[tuple]) -> list[tuple]:
        resolved: list[tuple] = []
        for group in RuntimeDiagnosis._incident_groups(failures):
            classes = {item[1] for item in group}
            request_failure_classes = {
                FailureClass.DECLARED_HTTP_ANOMALY,
                FailureClass.HTTP_SERVER_ERROR,
                FailureClass.REQUEST_PROCESSING_FAILURE,
            }
            if classes <= request_failure_classes:
                preferred = max(
                    classes,
                    key={
                        FailureClass.DECLARED_HTTP_ANOMALY: 1,
                        FailureClass.HTTP_SERVER_ERROR: 2,
                        FailureClass.REQUEST_PROCESSING_FAILURE: 3,
                    }.__getitem__,
                )
                resolved.extend(item for item in group if item[1] is preferred)
            else:
                resolved.extend(group)
        return resolved

    @staticmethod
    def _incident_groups(signals: list[tuple]) -> list[list[tuple]]:
        parents = list(range(len(signals)))

        def find(index: int) -> int:
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parents[right_root] = left_root

        identity_owner: dict[str, int] = {}
        for index, signal in enumerate(signals):
            for identity in signal[3]:
                owner = identity_owner.setdefault(identity, index)
                union(owner, index)

        groups: dict[int, list[tuple]] = {}
        for index, signal in enumerate(signals):
            groups.setdefault(find(index), []).append(signal)
        return list(groups.values())

    @staticmethod
    def _reference(record: RuntimeEvidence) -> EvidenceReference:
        return EvidenceReference(
            evidence_id=record.evidence_id,
            evidence_hash=record.evidence_hash,
            source_id=record.source_id,
            source_event_id=record.source_event_id,
        )

    @staticmethod
    def _insufficient(
        evidence: tuple[EvidenceReference, ...], reason: str
    ) -> DiagnosisReport:
        return DiagnosisReport(
            diagnosis_id=str(uuid.uuid4()),
            created_at=dt.datetime.now(dt.UTC),
            detection=FailureDetection.INSUFFICIENT_EVIDENCE,
            confidence=0.0,
            evidence=evidence,
            uncertainty_reason=reason,
        )

    @staticmethod
    def _recommendation(
        failure_class: FailureClass,
        evidence_ids: tuple[str, ...],
        *,
        suspected: bool = False,
    ) -> RemediationRecommendation:
        titles = {
            FailureClass.HTTP_SERVER_ERROR: "Investigate the affected server-error request",
            FailureClass.DECLARED_HTTP_ANOMALY: "Validate the configured HTTP anomaly",
            FailureClass.REQUEST_PROCESSING_FAILURE: "Review the correlated request failure",
            FailureClass.SERVICE_HEALTH_FAILURE: "Investigate the unhealthy service signal",
        }
        if suspected:
            title = titles[failure_class]
            action = (
                "A human operator should verify that this status is anomalous under the "
                "service's declared operational policy before treating it as an incident."
            )
            effect = "Confirm whether the configured anomaly rule represents a real incident."
            risk = (
                "The signal may be expected traffic or policy behavior. Do not change production "
                "state based on this suspected anomaly alone."
            )
        else:
            title = titles[failure_class]
            action = (
                "A human operator should inspect the cited evidence and correlate it with "
                "the service's approved logs and dependency health before selecting a fix."
            )
            effect = "Narrow the cause using evidence without changing production state."
            risk = (
                "Investigation is read-only. Any later operational change requires separate "
                "authorization and a reviewed change procedure."
            )
        return RemediationRecommendation(
            recommendation_id=str(uuid.uuid4()),
            title=title,
            action=action,
            expected_effect=effect,
            risk=risk,
            verification_steps=(
                "Confirm the source and timestamp of each cited event.",
                "Correlate the event with adjacent logs and dependency health.",
                "If a separately approved fix is applied, rerun the failing request "
                "or health probe.",
            ),
            evidence_ids=evidence_ids,
        )
