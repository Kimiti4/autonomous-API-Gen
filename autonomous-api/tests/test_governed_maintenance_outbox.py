import json

import pytest

from app.engine.governed_maintenance_outbox import SQLiteObservatoryOutbox


def payload(event_id="maintenance-sha256-abc"):
    return {
        "id": event_id,
        "source": "esap.governed-maintenance",
        "type": "governed_maintenance_recorded",
        "payload": {"status": "verified", "digest": "abc"},
    }


def test_enqueue_is_durable_and_duplicate_is_idempotent(tmp_path):
    path = tmp_path / "outbox.sqlite3"
    first = SQLiteObservatoryOutbox(path)
    assert first.enqueue("maintenance-sha256-abc", payload()) is True
    assert first.enqueue("maintenance-sha256-abc", payload()) is False

    reopened = SQLiteObservatoryOutbox(path)
    queued = reopened.pending()
    assert len(queued) == 1
    assert queued[0].payload == payload()
    assert queued[0].attempts == 0


def test_rejects_reuse_of_idempotency_key_with_different_payload(tmp_path):
    outbox = SQLiteObservatoryOutbox(tmp_path / "outbox.sqlite3")
    outbox.enqueue("maintenance-sha256-abc", payload())
    changed = payload()
    changed["payload"]["status"] = "pending"

    with pytest.raises(ValueError, match="outbox-idempotency-key-payload-conflict"):
        outbox.enqueue("maintenance-sha256-abc", changed)


@pytest.mark.parametrize(
    ("event_id", "body", "message"),
    [
        ("", payload(""), "outbox-event-id-required"),
        ("different-id", payload(), "outbox-event-id-payload-mismatch"),
        ("maintenance-sha256-abc", [], "outbox-payload-must-be-object"),
    ],
)
def test_rejects_invalid_event_identity_and_payload(tmp_path, event_id, body, message):
    outbox = SQLiteObservatoryOutbox(tmp_path / "outbox.sqlite3")
    with pytest.raises(ValueError, match=message):
        outbox.enqueue(event_id, body)


def test_delivery_failure_is_retained_and_retried_with_identical_payload(tmp_path):
    outbox = SQLiteObservatoryOutbox(tmp_path / "outbox.sqlite3")
    event = payload()
    outbox.enqueue(event["id"], event)
    seen = []

    def unavailable(body):
        seen.append(json.dumps(body, sort_keys=True))
        raise TimeoutError("observatory timeout")

    failed = outbox.deliver_pending(unavailable)
    assert (failed.delivered, failed.failed, failed.pending) == (0, 1, 1)
    status = outbox.get_status(event["id"])
    assert status["status"] == "pending"
    assert status["attempts"] == 1
    assert "TimeoutError" in status["last_error"]

    def recovered(body):
        seen.append(json.dumps(body, sort_keys=True))
        return "observatory-event-17"

    retried = outbox.deliver_pending(recovered)
    assert (retried.delivered, retried.failed, retried.pending) == (1, 0, 0)
    assert seen[0] == seen[1]
    status = outbox.get_status(event["id"])
    assert status["status"] == "delivered"
    assert status["attempts"] == 2
    assert status["remote_event_id"] == "observatory-event-17"
    assert status["last_error"] is None


def test_invalid_acknowledgement_stays_pending(tmp_path):
    outbox = SQLiteObservatoryOutbox(tmp_path / "outbox.sqlite3")
    event = payload()
    outbox.enqueue(event["id"], event)

    summary = outbox.deliver_pending(lambda _body: "   ")
    assert summary.failed == 1
    assert summary.pending == 1
    assert outbox.get_status(event["id"])["status"] == "pending"


def test_pending_limit_must_be_positive_integer(tmp_path):
    outbox = SQLiteObservatoryOutbox(tmp_path / "outbox.sqlite3")
    for value in (0, -1, True, 1.5):
        with pytest.raises(ValueError, match="outbox-limit-must-be-positive-integer"):
            outbox.pending(value)
