import json
import sqlite3

import pytest

from app.engine.deployed_app_observation import (
    ObservationStatus,
    RuntimeObservation,
    assess_deployed_observation,
)
from app.engine.governed_maintenance_execution import record_verified_maintenance
from app.engine.governed_maintenance_outbox import MaintenanceOutbox, MaintenanceOutboxError
from app.engine.repair_report import build_repair_report


class FakeResponse:
    status = 200

    def read(self):
        return json.dumps({"status": "accepted", "event_id": "evt-outbox-1"}).encode()

    def close(self):
        pass


def maintenance_case():
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
    return record_verified_maintenance(
        observation,
        admission,
        obligation_id="ob-17",
        authorization_ref="approval:ticket-17",
        repair_report=report,
    )


def test_enqueue_is_durable_and_idempotent(tmp_path):
    path = tmp_path / "maintenance-outbox.sqlite3"
    record, event = maintenance_case()
    outbox = MaintenanceOutbox(path)

    assert outbox.enqueue(record, event) == event.digest
    assert outbox.enqueue(record, event) == event.digest
    assert outbox.summary() == {
        "pending": 1, "delivering": 0, "delivered": 0, "dead_letter": 0
    }

    reopened = MaintenanceOutbox(path)
    item = reopened.get(event.digest)
    assert item["status"] == "pending"
    assert item["attempts"] == 0


def test_enqueue_rejects_unverified_or_mismatched_event(tmp_path):
    from dataclasses import replace

    record, event = maintenance_case()
    outbox = MaintenanceOutbox(tmp_path / "outbox.sqlite3")
    with pytest.raises(ValueError, match="maintenance-event-not-verified"):
        outbox.enqueue(record, replace(event, status="pending"))
    with pytest.raises(ValueError, match="maintenance-event-record-linkage-mismatch"):
        outbox.enqueue(record, replace(event, obligation_id="ob-other"))


def test_delivery_failure_is_persisted_then_retried_after_backoff(tmp_path):
    now = [1000.0]
    record, event = maintenance_case()
    outbox = MaintenanceOutbox(
        tmp_path / "outbox.sqlite3",
        base_backoff_seconds=2,
        max_backoff_seconds=8,
        clock=lambda: now[0],
    )
    outbox.enqueue(record, event)

    failed = outbox.deliver_pending(
        base_url="https://observatory.example",
        token="test-token",
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("temporary outage")),
    )
    assert failed[0]["status"] == "pending"
    assert failed[0]["retry_in_seconds"] == 2
    assert outbox.get(event.digest)["attempts"] == 1
    assert outbox.get(event.digest)["last_error"].startswith("delivery-failed:")

    assert outbox.deliver_pending(
        base_url="https://observatory.example", token="test-token",
        opener=lambda *_args, **_kwargs: pytest.fail("backoff must prevent early retry"),
    ) == []

    now[0] += 2
    delivered = outbox.deliver_pending(
        base_url="https://observatory.example",
        token="test-token",
        opener=lambda *_args, **_kwargs: FakeResponse(),
    )
    assert delivered[0]["status"] == "delivered"
    assert delivered[0]["observatory_event_id"] == "evt-outbox-1"
    assert outbox.get(event.digest)["attempts"] == 2
    assert outbox.summary()["delivered"] == 1


def test_exhausted_delivery_is_dead_lettered_and_can_be_requeued(tmp_path):
    now = [50.0]
    record, event = maintenance_case()
    outbox = MaintenanceOutbox(
        tmp_path / "outbox.sqlite3",
        max_attempts=1,
        clock=lambda: now[0],
    )
    outbox.enqueue(record, event)
    result = outbox.deliver_pending(
        base_url="https://observatory.example",
        token="test-token",
        opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    assert result[0]["status"] == "dead_letter"
    assert outbox.summary()["dead_letter"] == 1
    assert outbox.retry_dead_letter(event.digest) is True
    assert outbox.get(event.digest)["status"] == "pending"
    assert outbox.get(event.digest)["attempts"] == 0
    assert outbox.retry_dead_letter(event.digest) is False


def test_digest_collision_does_not_overwrite_existing_evidence(tmp_path):
    from dataclasses import replace

    record, event = maintenance_case()
    outbox = MaintenanceOutbox(tmp_path / "outbox.sqlite3")
    outbox.enqueue(record, event)
    altered_record = replace(record, authorization_ref="approval:other")
    with pytest.raises(MaintenanceOutboxError, match="outbox-event-digest-collision"):
        outbox.enqueue(altered_record, event)
    assert outbox.get(event.digest)["status"] == "pending"


def test_outbox_rejects_invalid_configuration(tmp_path):
    with pytest.raises(ValueError, match="outbox-database-must-be-durable"):
        MaintenanceOutbox(":memory:")
    with pytest.raises(ValueError, match="outbox-max-attempts-invalid"):
        MaintenanceOutbox(tmp_path / "outbox.sqlite3", max_attempts=0)
    with pytest.raises(ValueError, match="outbox-lease-invalid"):
        MaintenanceOutbox(tmp_path / "outbox.sqlite3", lease_seconds=float("nan"))


def test_invalid_delivery_configuration_does_not_consume_attempts(tmp_path):
    record, event = maintenance_case()
    outbox = MaintenanceOutbox(tmp_path / "outbox.sqlite3")
    outbox.enqueue(record, event)
    with pytest.raises(ValueError, match="observatory-base-url-invalid"):
        outbox.deliver_pending(base_url="http://observatory.example", token="test-token")
    item = outbox.get(event.digest)
    assert item["status"] == "pending"
    assert item["attempts"] == 0



def test_expired_delivery_lease_is_recovered_after_reopen(tmp_path):
    path = tmp_path / "maintenance-outbox.sqlite3"
    now = [1000.0]
    record, event = maintenance_case()
    first_process = MaintenanceOutbox(
        path,
        lease_seconds=3,
        base_backoff_seconds=2,
        clock=lambda: now[0],
    )
    first_process.enqueue(record, event)

    # Simulate a worker process stopping after claiming an event but before
    # persisting a delivery result. The lease must make it recoverable.
    claimed = first_process._claim(limit=1)
    assert len(claimed) == 1
    assert first_process.get(event.digest)["status"] == "delivering"
    assert first_process.get(event.digest)["attempts"] == 1

    now[0] += 4
    restarted_process = MaintenanceOutbox(
        path,
        lease_seconds=3,
        base_backoff_seconds=2,
        clock=lambda: now[0],
    )
    result = restarted_process.deliver_pending(
        base_url="https://observatory.example",
        token="test-token",
        opener=lambda *_args, **_kwargs: FakeResponse(),
    )

    assert result[0]["status"] == "delivered"
    assert result[0]["attempts"] == 2
    persisted = restarted_process.get(event.digest)
    assert persisted["status"] == "delivered"
    assert persisted["observatory_event_id"] == "evt-outbox-1"
    assert restarted_process.summary() == {
        "pending": 0, "delivering": 0, "delivered": 1, "dead_letter": 0
    }


def test_outbox_sqlite_database_survives_reopen_with_pending_item(tmp_path):
    path = tmp_path / "maintenance-outbox.sqlite3"
    record, event = maintenance_case()
    first_process = MaintenanceOutbox(path)
    first_process.enqueue(record, event)
    first_process_path = first_process.database_path

    # Close the only open connections by leaving the API and reopen the same
    # file, as a replacement process/container would do with a mounted volume.
    with sqlite3.connect(first_process_path) as connection:
        assert connection.execute(
            "SELECT status, attempts FROM maintenance_outbox WHERE event_digest = ?",
            (event.digest,),
        ).fetchone() == ("pending", 0)

    restarted_process = MaintenanceOutbox(path)
    persisted = restarted_process.get(event.digest)
    assert persisted["status"] == "pending"
    assert persisted["attempts"] == 0
    assert restarted_process.enqueue(record, event) == event.digest
    assert restarted_process.summary()["pending"] == 1
