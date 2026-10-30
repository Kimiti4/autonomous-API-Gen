from __future__ import annotations

import datetime as dt
import os
import subprocess

import pytest
from pydantic import ValidationError

from tiannara.application.diagnosis import (
    DiagnosisInputError,
    EvidenceIngestionError,
    RuntimeDiagnosis,
)
from tiannara.domain.models.diagnosis import (
    DiagnosisSeverity,
    DiagnosisReport,
    FailureClass,
    FailureDetection,
    RecommendationExecution,
    ReviewDecision,
    RootCauseStatus,
    RuntimeEvidence,
    VerificationOutcome,
)


UTC = dt.timezone.utc
ENGINE = RuntimeDiagnosis()


def _evidence(
    event_id: str,
    event_name: str,
    payload: dict,
    *,
    evidence_id: str | None = None,
    source_id: str = "service-a",
    observed_at: dt.datetime | None = None,
) -> RuntimeEvidence:
    return RuntimeEvidence.create(
        evidence_id=evidence_id or f"evidence-{event_id}",
        source_id=source_id,
        source_kind="generated_service_log",
        source_event_id=event_id,
        event_name=event_name,
        observed_at=observed_at or dt.datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
        payload=payload,
    )


def test_evidence_contract_requires_provenance_supported_schema_and_valid_hash():
    with pytest.raises(ValidationError, match="source_id"):
        RuntimeEvidence.create(
            evidence_id="e1",
            source_id="",
            source_kind="runtime",
            source_event_id="evt-1",
            event_name="http.request.completed",
            observed_at=dt.datetime.now(UTC),
            payload={"status_code": 503},
        )
    with pytest.raises(ValidationError, match="valid datetime"):
        RuntimeEvidence.model_validate(
            {
                "evidence_id": "e1",
                "source_id": "source",
                "source_kind": "generated_service_log",
                "source_event_id": "evt-1",
                "schema_version": "1.0",
                "event_name": "http.request.completed",
                "observed_at": "not-a-timestamp",
                "payload": {"status_code": 503},
                "evidence_hash": "0" * 64,
            }
        )

    with pytest.raises(ValidationError, match="timezone"):
        RuntimeEvidence.create(
            evidence_id="e1",
            source_id="source",
            source_kind="runtime",
            source_event_id="evt-1",
            event_name="http.request.completed",
            observed_at=dt.datetime(2026, 10, 30),
            payload={"status_code": 503},
        )

    with pytest.raises(ValidationError, match="unsupported runtime event"):
        _evidence("evt-2", "database.connection.failed", {})
    with pytest.raises(ValidationError, match="source_kind"):
        RuntimeEvidence.create(
            evidence_id="e1",
            source_id="source",
            source_kind="unknown-transport",
            source_event_id="evt-1",
            event_name="http.request.completed",
            observed_at=dt.datetime.now(UTC),
            payload={"status_code": 503},
        )

    valid = _evidence("evt-3", "http.request.completed", {"status_code": 503})
    altered = valid.model_dump()
    altered["payload"] = {"status_code": 200}
    with pytest.raises(ValidationError, match="does not match"):
        RuntimeEvidence.model_validate(altered)


def test_malformed_supported_event_payload_is_rejected():
    with pytest.raises(ValidationError, match="status_code"):
        _evidence("evt-1", "http.request.completed", {"status_code": "503"})
    with pytest.raises(ValidationError, match="error_id"):
        _evidence("evt-2", "http.request.failed", {"error_id": ""})
    with pytest.raises(ValidationError, match="service.health requires"):
        _evidence("evt-3", "service.health", {})


def test_known_http_failure_is_classified_and_cited_without_cause_claim():
    item = _evidence(
        "evt-503",
        "http.request.completed",
        {"request_id": "req-503", "status_code": 503, "route": "/orders"},
    )
    report = ENGINE.diagnose([item])

    assert report.detection is FailureDetection.CONFIRMED_FAILURE
    assert report.failure_class is FailureClass.HTTP_SERVER_ERROR
    assert report.severity is DiagnosisSeverity.HIGH
    assert report.confidence == 0.90
    assert [ref.evidence_id for ref in report.evidence] == [item.evidence_id]
    assert report.hypotheses[0].status is RootCauseStatus.HYPOTHESIS
    assert report.hypotheses[0].evidence_ids == (item.evidence_id,)
    assert report.recommendations[0].evidence_ids == (item.evidence_id,)
    assert report.recommendations[0].execution is RecommendationExecution.NOT_EXECUTED
    assert report.hypotheses[0].confidence <= report.confidence
    with pytest.raises(ValidationError, match="execution"):
        type(report.recommendations[0]).model_validate(
            {**report.recommendations[0].model_dump(), "execution": "executed"}
        )


def test_explicit_error_event_is_confirmed_but_does_not_confirm_root_cause():
    item = _evidence(
        "evt-error",
        "http.request.failed",
        {"request_id": "req-error", "error_id": "err-123"},
    )
    report = ENGINE.diagnose([item])

    assert report.failure_class is FailureClass.REQUEST_PROCESSING_FAILURE
    assert report.confidence == 0.95
    assert all(h.status is RootCauseStatus.HYPOTHESIS for h in report.hypotheses)


def test_error_event_and_5xx_completion_for_same_request_are_one_incident():
    failed = _evidence(
        "evt-failed",
        "http.request.failed",
        {"request_id": "same-request", "error_id": "err-1"},
    )
    completed = _evidence(
        "evt-completed",
        "http.request.completed",
        {"request_id": "same-request", "status_code": 500},
    )
    report = ENGINE.diagnose([completed, failed])
    assert report.detection is FailureDetection.CONFIRMED_FAILURE
    assert report.failure_class is FailureClass.REQUEST_PROCESSING_FAILURE
    assert set(report.hypotheses[0].evidence_ids) == {
        failed.evidence_id
    }


def test_health_failure_is_detected():
    item = _evidence("evt-health", "service.health", {"status": "unhealthy"})
    report = ENGINE.diagnose([item])
    assert report.detection is FailureDetection.CONFIRMED_FAILURE
    assert report.failure_class is FailureClass.SERVICE_HEALTH_FAILURE


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status_code": 200},
        {"status_code": 404},
        {"status_code": 499},
        {"status_code": 599 - 100},
    ],
)
def test_non_failure_or_incomplete_events_do_not_invent_diagnoses(payload):
    item = _evidence("evt-neutral", "http.request.completed", payload)
    report = ENGINE.diagnose([item])
    assert report.detection is FailureDetection.INSUFFICIENT_EVIDENCE
    assert report.failure_class is None
    assert report.hypotheses == ()
    assert report.recommendations == ()
    assert report.uncertainty_reason


def test_suspected_anomalies_require_an_explicit_rule():
    rate_limited = _evidence(
        "evt-429",
        "http.request.completed",
        {"request_id": "req-429", "status_code": 429},
    )
    assert ENGINE.diagnose([rate_limited]).detection is FailureDetection.INSUFFICIENT_EVIDENCE

    configured = RuntimeDiagnosis(suspected_status_codes=(429,))
    report = configured.diagnose([rate_limited])
    assert report.detection is FailureDetection.SUSPECTED_FAILURE
    assert report.failure_class is FailureClass.DECLARED_HTTP_ANOMALY
    assert report.severity is DiagnosisSeverity.MEDIUM
    assert report.confidence == 0.55
    assert "before treating it as an incident" in report.recommendations[0].action
    assert report.recommendations[0].execution is RecommendationExecution.NOT_EXECUTED

    with pytest.raises(ValueError, match="suspected_status_codes"):
        RuntimeDiagnosis(suspected_status_codes=(503,))


def test_duplicate_evidence_is_deduplicated_and_conflicting_reuse_rejected():
    item = _evidence("evt-duplicate", "http.request.completed", {"status_code": 503})
    report = ENGINE.diagnose([item, item])
    assert len(report.evidence) == 1

    reused_identity = _evidence(
        "evt-duplicate",
        "http.request.completed",
        {"status_code": 500},
        evidence_id="different-evidence-id",
    )
    with pytest.raises(EvidenceIngestionError, match="source event identity"):
        ENGINE.diagnose([item, reused_identity])

    changed_id_same_ref = _evidence(
        "evt-another",
        "http.request.completed",
        {"status_code": 500},
        evidence_id=item.evidence_id,
    )
    with pytest.raises(EvidenceIngestionError, match="conflicting content"):
        ENGINE.diagnose([item, changed_id_same_ref])

    mutated = _evidence(
        "evt-mutated",
        "http.request.completed",
        {"status_code": 503},
    )
    mutated.payload["status_code"] = 200
    with pytest.raises(EvidenceIngestionError, match="integrity validation"):
        ENGINE.ingest([mutated])


def test_conflicting_signals_for_same_request_remain_uncertain():
    failed = _evidence(
        "evt-failed",
        "http.request.failed",
        {"request_id": "same-request", "error_id": "err-1"},
    )
    success = _evidence(
        "evt-success",
        "http.request.completed",
        {"request_id": "same-request", "status_code": 200},
    )
    report = ENGINE.diagnose([failed, success])
    assert report.detection is FailureDetection.CONFLICTING_EVIDENCE
    assert report.failure_class is None
    assert report.hypotheses == ()
    assert report.recommendations == ()


def test_records_from_different_sources_with_same_source_event_id_are_not_deduped():
    first = _evidence("evt-same", "http.request.completed", {"status_code": 503}, source_id="a")
    second = _evidence(
        "evt-same",
        "http.request.completed",
        {"status_code": 503},
        evidence_id="evidence-from-b",
        source_id="b",
    )
    assert len(ENGINE.ingest([first, second])) == 2


def test_review_is_recorded_but_never_executes_recommendation():
    item = _evidence(
        "evt-503",
        "http.request.completed",
        {"request_id": "req-503", "status_code": 503},
    )
    report = ENGINE.diagnose([item])
    recommendation = report.recommendations[0]
    reviewed = ENGINE.review(
        report,
        recommendation_id=recommendation.recommendation_id,
        reviewer_id="operator-7",
        decision=ReviewDecision.ACCEPTED,
        rationale="Approved for read-only investigation.",
        verification_outcome=VerificationOutcome.NOT_RUN,
    )

    assert len(reviewed.reviews) == 1
    assert reviewed.reviews[0].reviewer_id == "operator-7"
    assert reviewed.reviews[0].decision is ReviewDecision.ACCEPTED
    assert reviewed.reviews[0].verification_outcome is VerificationOutcome.NOT_RUN
    assert reviewed.recommendations[0].execution is RecommendationExecution.NOT_EXECUTED
    with pytest.raises(DiagnosisInputError, match="distinct from recommendation evidence"):
        ENGINE.review(
            report,
            recommendation_id=recommendation.recommendation_id,
            reviewer_id="operator-7",
            decision=ReviewDecision.ACCEPTED,
            rationale="Replay cannot verify the recommendation.",
            verification_outcome=VerificationOutcome.PASSED,
            verification_evidence=[item],
        )
    with pytest.raises(DiagnosisInputError, match="unknown recommendation"):
        ENGINE.review(
            report,
            recommendation_id="not-in-this-report",
            reviewer_id="operator-7",
            decision=ReviewDecision.ACCEPTED,
            rationale="This must not be accepted.",
        )


def test_verification_outcome_requires_evidence_and_reviews_are_report_bound():
    item = _evidence("evt-503", "http.request.completed", {"status_code": 503})
    report = ENGINE.diagnose([item])
    with pytest.raises(DiagnosisInputError, match="verification evidence"):
        ENGINE.review(
            report,
            recommendation_id=report.recommendations[0].recommendation_id,
            reviewer_id="operator-7",
            decision=ReviewDecision.ACCEPTED,
            rationale="Verified.",
            verification_outcome=VerificationOutcome.PASSED,
        )
    verification_evidence = _evidence(
        "evt-verified",
        "http.request.completed",
        {"request_id": "req-recovered", "status_code": 200},
        evidence_id="evidence-verification",
        source_id="service-a",
    )
    reviewed = ENGINE.review(
        report,
        recommendation_id=report.recommendations[0].recommendation_id,
        reviewer_id="operator-7",
        decision=ReviewDecision.ACCEPTED,
        rationale="Follow-up request passed after the separately approved change.",
        verification_outcome=VerificationOutcome.PASSED,
        verification_evidence=[verification_evidence],
    )
    assert reviewed.reviews[0].verification_evidence_ids == (
        verification_evidence.evidence_id,
    )
    assert any(
        evidence.evidence_id == verification_evidence.evidence_id
        for evidence in reviewed.evidence
    )
    with pytest.raises(ValidationError, match="cannot confirm root cause"):
        DiagnosisReport.model_validate(
            {
                **report.model_dump(),
                "hypotheses": [
                    {
                        **report.hypotheses[0].model_dump(),
                        "status": RootCauseStatus.CONFIRMED,
                    }
                ],
            }
        )


def test_review_and_diagnosis_have_no_production_execution_side_effects(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("diagnosis attempted an operational side effect")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(os, "system", forbidden)
    item = _evidence(
        "evt-safe",
        "http.request.completed",
        {"request_id": "req-safe", "status_code": 503},
    )
    report = ENGINE.diagnose([item])
    reviewed = ENGINE.review(
        report,
        recommendation_id=report.recommendations[0].recommendation_id,
        reviewer_id="operator-safe",
        decision=ReviewDecision.ACCEPTED,
        rationale="Approved for read-only investigation.",
    )
    assert reviewed.recommendations[0].execution is RecommendationExecution.NOT_EXECUTED
