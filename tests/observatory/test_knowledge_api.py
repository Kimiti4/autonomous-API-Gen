"""Knowledge API tests: overview/detail contract over live TestClient."""
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
    base = {"source": "test", "category": "knowledge",
            "type": "knowledge_recorded", "subject_id": "KNOW-A",
            "payload": {"knowledge_id": "KNOW-A",
                        "statement": "Filtering worked."}}
    base.update(overrides)
    response = client.post("/observatory/events", json=base, headers=WRITER)
    assert response.status_code == 200, response.text
    return response


class KnowledgeApi(unittest.TestCase):
    def test_overview_empty(self):
        client = _client(self)
        response = client.get("/observatory/knowledge/overview")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_subjects_appear(self):
        client = _client(self)
        _emit(client)
        _emit(client, subject_id="KNOW-B",
              payload={"knowledge_id": "KNOW-B", "statement": "Second."})
        overview = client.get("/observatory/knowledge/overview").json()
        self.assertEqual([item["subject_id"] for item in overview],
                         ["KNOW-A", "KNOW-B"])
        self.assertEqual(overview[0]["epistemic_state"]["observed"], 1)

    def test_detail_sections(self):
        client = _client(self)
        _emit(client)
        client.post("/observatory/events", json={
            "source": "test", "category": "knowledge",
            "type": "unknown_recorded", "subject_id": "KNOW-A",
            "payload": {"knowledge_id": "KNOW-A", "unknown_id": "U-1",
                        "question": "UI proof?", "reason": "no UI evidence"},
            "epistemic_status": "unknown"}, headers=WRITER)
        detail = client.get("/observatory/knowledge/KNOW-A/memory")
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(len(body["facts"]), 1)
        self.assertEqual(len(body["unknowns"]), 1)
        self.assertEqual(body["unknowns"][0]["unknown_id"], "U-1")
        self.assertEqual(body["timeline"][0]["subject_id"], "KNOW-A")

    def test_detail_404(self):
        client = _client(self)
        missing = client.get("/observatory/knowledge/KNOW-nope/memory")
        self.assertEqual(missing.status_code, 404)

    def test_overview_not_captured_as_subject(self):
        # Route ordering: /overview must not resolve as subject "overview".
        client = _client(self)
        response = client.get("/observatory/knowledge/overview")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)


if __name__ == "__main__":
    unittest.main()
