"""Experiments API tests: overview/detail contract over live TestClient."""
from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from tests.observatory.conftest import register_store_cleanup

WRITER = {"X-Actor-Id": "writer-1", "X-Actor-Role": "operator",
          "X-Observatory-Token": "test-token"}


def _client(testcase: unittest.TestCase):
    import observatory.backend.main as main_module

    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    os.environ["OBSERVATORY_DB_PATH"] = os.path.join(tmp.name, "obs.sqlite3")
    os.environ["OBSERVATORY_API_TOKEN"] = "test-token"
    main_module.get_settings.cache_clear()
    from observatory.backend.main import create_app
    client = TestClient(create_app())
    register_store_cleanup(testcase, client)
    return client


def _emit(client, **overrides):
    base = {"source": "test", "category": "evolution",
            "type": "experiment_proposed", "subject_id": "EXP-1",
            "payload": {"experiment_id": "EXP-1",
                        "hypothesis": "Filtering works."}}
    base.update(overrides)
    response = client.post("/observatory/events", json=base, headers=WRITER)
    assert response.status_code == 200, response.text
    return response


class ExperimentsApi(unittest.TestCase):
    def test_overview_empty(self):
        client = _client(self)
        response = client.get("/observatory/experiments")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_lifecycle_populates(self):
        client = _client(self)
        _emit(client)
        _emit(client, type="experiment_authorized",
              payload={"experiment_id": "EXP-1"})
        _emit(client, type="experiment_completed",
              payload={"experiment_id": "EXP-1", "status": "completed"})
        overview = client.get("/observatory/experiments").json()
        self.assertEqual(len(overview), 1)
        self.assertEqual(overview[0]["status"], "completed")
        self.assertEqual(overview[0]["authorization_state"], "authorized")

    def test_detail_404(self):
        client = _client(self)
        missing = client.get("/observatory/experiments/EXP-nope")
        self.assertEqual(missing.status_code, 404)

    def test_detail_sections(self):
        client = _client(self)
        _emit(client)
        _emit(client, category="evidence", type="experiment_result",
              payload={"experiment_id": "EXP-1", "name": "filter-high",
                       "expected": "HIGH only", "observed": "HIGH only",
                       "passed": True})
        detail = client.get("/observatory/experiments/EXP-1").json()
        self.assertEqual(detail["hypothesis"], "Filtering works.")
        self.assertEqual(len(detail["results"]), 1)
        self.assertTrue(detail["results"][0]["passed"])
        self.assertEqual(detail["reproducibility"], "unknown")

    def test_rejected_renders(self):
        client = _client(self)
        _emit(client)
        _emit(client, type="experiment_rejected",
              payload={"experiment_id": "EXP-1"})
        overview = client.get("/observatory/experiments").json()
        self.assertEqual(overview[0]["status"], "rejected")
        self.assertEqual(overview[0]["authorization_state"], "rejected")

    def test_failed_renders(self):
        client = _client(self)
        _emit(client, type="experiment_failed",
              payload={"experiment_id": "EXP-1"})
        detail = client.get("/observatory/experiments/EXP-1").json()
        self.assertEqual(detail["status"], "failed")


if __name__ == "__main__":
    unittest.main()
