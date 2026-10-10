import logging

import pytest

from app.engine.maintenance_outbox_worker import main, run_once


class FakeOutbox:
    def __init__(self, database_path):
        self.database_path = database_path
        self.kwargs = None

    def deliver_pending(self, **kwargs):
        self.kwargs = kwargs
        return [{
            "event_digest": "a" * 64,
            "status": "delivered",
            "attempts": 1,
            "observatory_event_id": "evt-1",
            "error": None,
        }]


def worker_env(**overrides):
    env = {
        "MAINTENANCE_OUTBOX_DB_PATH": "/persistent/maintenance-outbox.sqlite3",
        "OBSERVATORY_BASE_URL": "https://observatory.example",
        "OBSERVATORY_API_TOKEN": "test-secret-token",
    }
    env.update(overrides)
    return env


def test_worker_delivers_only_one_bounded_batch():
    created = []

    def outbox_factory(path):
        fake = FakeOutbox(path)
        created.append(fake)
        return fake

    result = run_once(
        worker_env(
            MAINTENANCE_OUTBOX_BATCH_LIMIT="7",
            MAINTENANCE_OUTBOX_HTTP_TIMEOUT_SECONDS="3.5",
        ),
        outbox_factory=outbox_factory,
    )

    assert result[0]["status"] == "delivered"
    assert len(created) == 1
    fake = created[0]
    assert fake.database_path == "/persistent/maintenance-outbox.sqlite3"
    assert fake.kwargs == {
        "base_url": "https://observatory.example",
        "token": "test-secret-token",
        "timeout": 3.5,
        "limit": 7,
    }


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("MAINTENANCE_OUTBOX_DB_PATH", "", "maintenance-outbox-database-path-required"),
        ("OBSERVATORY_BASE_URL", "", "observatory-base-url-required"),
        ("OBSERVATORY_API_TOKEN", "", "observatory-token-required"),
        ("MAINTENANCE_OUTBOX_BATCH_LIMIT", "0", "maintenance-worker-integer-config-out-of-range"),
        ("MAINTENANCE_OUTBOX_BATCH_LIMIT", "101", "maintenance-worker-integer-config-out-of-range"),
        ("MAINTENANCE_OUTBOX_HTTP_TIMEOUT_SECONDS", "nan", "maintenance-worker-timeout-config-invalid"),
    ],
)
def test_worker_rejects_missing_or_invalid_configuration(key, value, message):
    with pytest.raises(ValueError, match=message):
        run_once(worker_env(**{key: value}), outbox_factory=FakeOutbox)


def test_worker_logs_metadata_without_logging_token_or_evidence(caplog):
    class FailingOutbox:
        def __init__(self, _path):
            pass

        def deliver_pending(self, **_kwargs):
            return [{
                "event_digest": "b" * 64,
                "status": "pending",
                "attempts": 1,
                "error": "delivery-failed:TimeoutError",
                "evidence_payload": "private-evidence",
            }]

    with caplog.at_level(logging.INFO, logger="maintenance_outbox_worker"):
        results = run_once(worker_env(), outbox_factory=FailingOutbox)

    assert results[0]["status"] == "pending"
    assert "test-secret-token" not in caplog.text
    assert "private-evidence" not in caplog.text
    assert "delivery-failed:TimeoutError" in caplog.text


def test_cli_returns_nonzero_for_delivery_failures(monkeypatch):
    monkeypatch.setattr(
        "app.engine.maintenance_outbox_worker.run_once",
        lambda: [{"status": "dead_letter"}],
    )
    assert main() == 1


def test_cli_returns_zero_when_batch_has_no_due_events(monkeypatch):
    monkeypatch.setattr(
        "app.engine.maintenance_outbox_worker.run_once",
        lambda: [],
    )
    assert main() == 0
