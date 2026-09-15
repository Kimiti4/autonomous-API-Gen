"""Batch endpoint contract tests (real HTTP boundary, temp DBs)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from observatory.backend.config import get_settings
from observatory.backend.main import create_app

from .conftest import OBSERVER_HEADERS, SYSTEM_HEADERS

TIMESTAMP = "2026-01-01T00:00:00+00:00"
BATCH_URL = "/observatory/events/batch"


def make_event(**overrides):
    event = {
        "source": "tiannara.test",
        "category": "runtime",
        "type": "test_event",
        "subject_id": "TEST-SUBJECT",
        "payload": {"summary": "test event"},
        "timestamp": TIMESTAMP,
    }
    event.update(overrides)
    return event


def test_empty_batch_is_rejected(client):
    response = client.post(BATCH_URL, json={"events": []},
                           headers=SYSTEM_HEADERS)
    assert response.status_code == 400
    assert response.json()["detail"] == "event batch is empty"


def test_valid_batch_is_accepted(client):
    events = [make_event(subject_id="SUBJECT-1"),
              make_event(subject_id="SUBJECT-2")]
    response = client.post(BATCH_URL, json={"events": events},
                           headers=SYSTEM_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["accepted"] == 2
    assert body["inserted"] == 2
    assert body["duplicates"] == 0
    assert len(body["event_ids"]) == 2


def test_duplicate_event_is_idempotent(client):
    event = make_event(id="evt-api-duplicate", subject_id="SUBJECT-DUPLICATE")
    first_response = client.post(BATCH_URL, json={"events": [event]},
                                 headers=SYSTEM_HEADERS)
    assert first_response.status_code == 200
    assert first_response.json()["inserted"] == 1
    assert first_response.json()["duplicates"] == 0
    second_response = client.post(BATCH_URL, json={"events": [event]},
                                  headers=SYSTEM_HEADERS)
    assert second_response.status_code == 200
    body = second_response.json()
    assert body["accepted"] == 1
    assert body["inserted"] == 0
    assert body["duplicates"] == 1
    assert body["event_ids"] == ["evt-api-duplicate"]


def test_same_event_id_with_different_payload_is_conflict(client):
    event_one = make_event(id="evt-api-conflict",
                           subject_id="SUBJECT-CONFLICT",
                           payload={"version": 1})
    event_two = make_event(id="evt-api-conflict",
                           subject_id="SUBJECT-CONFLICT",
                           payload={"version": 2})
    first_response = client.post(BATCH_URL, json={"events": [event_one]},
                                 headers=SYSTEM_HEADERS)
    assert first_response.status_code == 200
    second_response = client.post(BATCH_URL, json={"events": [event_two]},
                                  headers=SYSTEM_HEADERS)
    assert second_response.status_code == 409
    assert second_response.json()["error"] == "store_integrity_error"


def test_invalid_event_reports_index(client):
    good_event = make_event(subject_id="GOOD")
    bad_event = make_event(source="", subject_id="BAD")
    response = client.post(BATCH_URL, json={"events": [good_event, bad_event]},
                           headers=SYSTEM_HEADERS)
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "invalid_event"
    assert detail["index"] == 1


def test_observer_role_cannot_ingest_events(client):
    response = client.post(BATCH_URL, json={"events": [make_event()]},
                           headers=OBSERVER_HEADERS)
    assert response.status_code == 403
    assert response.json()["detail"] == "writer role required"


def test_oversized_batch_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSERVATORY_DB_PATH",
                       str(tmp_path / "observatory.sqlite3"))
    monkeypatch.setenv("OBSERVATORY_API_TOKEN", "")
    monkeypatch.setenv("OBSERVATORY_MAX_BATCH_SIZE", "2")
    get_settings.cache_clear()
    app = create_app()
    try:
        with TestClient(app) as test_client:
            events = [make_event(subject_id=f"SUBJECT-{index}")
                      for index in range(3)]
            response = test_client.post(BATCH_URL, json={"events": events},
                                        headers=SYSTEM_HEADERS)
            assert response.status_code == 413
            assert (response.json()["detail"]
                    == "event batch exceeds maximum size of 2")
    finally:
        get_settings.cache_clear()
