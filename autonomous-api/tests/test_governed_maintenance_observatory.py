import json
from dataclasses import replace

import pytest

from app.engine.deployed_app_observation import (
    ObservationStatus,
    RuntimeObservation,
    assess_deployed_observation,
)
from app.engine.governed_maintenance_execution import record_verified_maintenance
from app.engine.governed_maintenance_observatory import (
    ObservatoryDeliveryError,
    deliver_maintenance_event,
    record_and_deliver_verified_maintenance,
)
from app.engine.repair_report import build_repair_report


class FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status = status
        self.payload = payload if payload is not None else {
            "status": "accepted", "event_id": "evt-evidence-abc123"
        }
        self.closed = False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def close(self):
        self.closed = True


def maintenance_inputs():
    observation = RuntimeObservation(
        deployment_id="staging-1",
        observed_revision="rev-a",
        environment_fingerprint="env-a",
        status=ObservationStatus.HEALTHY,
        health_evidence=("health:pass",),
        verification_evidence=("smoke:pass",),
    )
    admission = assess_deployed_observation(
        observation,
        baseline_revision="rev-a",
        baseline_environment_fingerprint="env-a",
        authorized_obligation_ids=("ob-17",),
        explicit_change_authorization=True,
    )
    report = build_repair_report(
        report_id="repair-17",
        target="staging-1",
        source_revision="rev-a",
        finding_ids=("finding-1",),
        root_causes=(),
        candidates_considered=(),
        selected_candidate_id="repair-candidate-1",
        patch_digest="sha256:patch-123",
        verification=({"passed": True, "evidence_refs": ("ci:run-17", "regression:run-17")},),
        regressions=({"detected": False, "evidence_ref": "regression:run-17"},),
        measurements=(),
        residuals=(),
        deployment_ready=False,
    )
    return observation, admission, report


def maintenance_case():
    observation, admission, report = maintenance_inputs()
    return record_verified_maintenance(
        observation, admission, obligation_id="ob-17",
        authorization_ref="approval:ticket-17", repair_report=report,
    )


def test_delivers_verified_event_to_observatory_and_checks_acknowledgement():
    record, event = maintenance_case()
    seen = {}

    def opener(request, *, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return FakeResponse()

    event_id = deliver_maintenance_event(
        record, event, base_url="https://observatory.example/", token="test-token",
        opener=opener,
    )
    request = seen["request"]
    body = json.loads(request.data.decode("utf-8"))
    assert event_id == "evt-evidence-abc123"
    assert request.full_url == "https://observatory.example/observatory/events"
    assert request.get_method() == "POST"
    assert request.get_header("X-observatory-token") == "test-token"
    assert request.get_header("X-actor-role") == "system"
    assert body["type"] == "governed_maintenance_recorded"
    assert body["payload"]["maintenance_event_digest"] == event.digest
    assert body["payload"]["authorization_ref"] == record.authorization_ref
    assert event.digest in body["evidence_refs"]
    assert seen["timeout"] == 5.0


@pytest.mark.parametrize(
    ("base_url", "token", "message"),
    [
        ("", "test-token", "observatory-base-url-required"),
        ("https://observatory.example", "", "observatory-token-required"),
    ],
)
def test_delivery_requires_explicit_endpoint_and_token(base_url, token, message):
    record, event = maintenance_case()
    with pytest.raises(ValueError, match=message):
        deliver_maintenance_event(record, event, base_url=base_url, token=token)


def test_delivery_rejects_non_verified_event():
    record, event = maintenance_case()
    pending = replace(event, status="pending")
    with pytest.raises(ValueError, match="maintenance-event-not-verified"):
        deliver_maintenance_event(
            record, pending, base_url="https://observatory.example",
            token="test-token", opener=lambda *_args, **_kwargs: pytest.fail("must not send"),
        )


def test_delivery_rejects_non_successful_http_response():
    record, event = maintenance_case()
    with pytest.raises(ObservatoryDeliveryError, match="observatory-event-ingestion-rejected"):
        deliver_maintenance_event(
            record, event, base_url="https://observatory.example", token="test-token",
            opener=lambda *_args, **_kwargs: FakeResponse(status=403),
        )


def test_delivery_rejects_success_without_observatory_acknowledgement():
    record, event = maintenance_case()
    with pytest.raises(ObservatoryDeliveryError, match="observatory-acknowledgement-invalid"):
        deliver_maintenance_event(
            record, event, base_url="https://observatory.example", token="test-token",
            opener=lambda *_args, **_kwargs: FakeResponse(payload={"status": "accepted"}),
        )


def test_delivery_rejects_event_linked_to_different_record():
    record, event = maintenance_case()
    mismatched = replace(event, obligation_id="ob-other")
    with pytest.raises(ValueError, match="maintenance-event-record-linkage-mismatch"):
        deliver_maintenance_event(
            record, mismatched, base_url="https://observatory.example",
            token="test-token", opener=lambda *_args, **_kwargs: pytest.fail("must not send"),
        )


def test_delivery_rejects_tampered_event_digest():
    record, event = maintenance_case()
    tampered = replace(event, digest="0" * 64)
    with pytest.raises(ValueError, match="maintenance-event-digest-mismatch"):
        deliver_maintenance_event(
            record, tampered, base_url="https://observatory.example",
            token="test-token", opener=lambda *_args, **_kwargs: pytest.fail("must not send"),
        )



def test_combined_flow_returns_only_after_observatory_acknowledges():
    observation, admission, report = maintenance_inputs()
    result = record_and_deliver_verified_maintenance(
        observation, admission, obligation_id="ob-17",
        authorization_ref="approval:ticket-17", repair_report=report,
        base_url="https://observatory.example", token="test-token",
        opener=lambda *_args, **_kwargs: FakeResponse(),
    )
    record, event, event_id = result
    assert record.observation_digest == observation.digest
    assert event.repair_report_digest == report.digest
    assert event_id == "evt-evidence-abc123"
