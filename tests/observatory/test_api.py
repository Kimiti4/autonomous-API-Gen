"""Observatory API contract tests (in-process FastAPI TestClient).

Covers read views, ingestion auth, command auth, trace/explain,
not-found mapping, and the SSE stream handshake. No network, no server.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from tests.observatory.conftest import register_store_cleanup


def _client(testcase: unittest.TestCase, token: str | None = "test-token"):
    import observatory.backend.main as main_module

    tmp = tempfile.TemporaryDirectory()
    # LIFO: tmp.cleanup registered first so the store closes first.
    testcase.addCleanup(tmp.cleanup)
    os.environ["OBSERVATORY_DB_PATH"] = os.path.join(tmp.name, "obs.sqlite3")
    if token is None:
        os.environ.pop("OBSERVATORY_API_TOKEN", None)
    else:
        os.environ["OBSERVATORY_API_TOKEN"] = token
    main_module.get_settings.cache_clear()
    from observatory.backend.main import create_app
    client = TestClient(create_app())
    register_store_cleanup(testcase, client)
    try:
        testcase.addCleanup(client.close)
    except AttributeError:
        pass
    return client


WRITER = {"X-Actor-Id": "writer-1", "X-Actor-Role": "operator",
          "X-Observatory-Token": "test-token"}
OPERATOR = {"X-Actor-Id": "op-1", "X-Actor-Role": "operator",
            "X-Actor-Clearance": "operator",
            "X-Observatory-Token": "test-token"}
OBSERVER = {"X-Actor-Id": "obs-1", "X-Actor-Role": "observer",
            "X-Observatory-Token": "test-token"}

EVENT = {"source": "test", "category": "runtime", "type": "process_started",
         "subject_id": "SUBJ-1"}


class ApiContract(unittest.TestCase):
    def test_meta_and_health(self):
        client = _client(self)
        self.assertEqual(client.get("/healthz").status_code, 200)
        self.assertEqual(client.get("/").status_code, 200)

    def test_read_views_empty(self):
        client = _client(self)
        for path in ("/observatory/dashboard", "/observatory/overview",
                     "/observatory/runtime", "/observatory/governance",
                     "/observatory/health", "/observatory/timeline",
                     "/observatory/knowledge"):
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_ingest_requires_writer(self):
        client = _client(self)
        denied = client.post("/observatory/events", json=EVENT,
                             headers=OBSERVER)
        self.assertEqual(denied.status_code, 403)
        accepted = client.post("/observatory/events", json=EVENT,
                               headers=WRITER)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["status"], "accepted")

    def test_ingest_bad_token(self):
        client = _client(self)
        headers = dict(WRITER, **{"X-Observatory-Token": "wrong"})
        denied = client.post("/observatory/events", json=EVENT,
                             headers=headers)
        self.assertEqual(denied.status_code, 401)

    def test_trace_explain_roundtrip(self):
        client = _client(self)
        client.post("/observatory/events", json=EVENT, headers=WRITER)
        trace = client.get("/observatory/trace/SUBJ-1")
        self.assertEqual(trace.status_code, 200)
        self.assertEqual(len(trace.json()), 1)
        explained = client.get("/observatory/explain/SUBJ-1")
        self.assertEqual(explained.status_code, 200)
        self.assertEqual(explained.json()["subject_id"], "SUBJ-1")

    def test_not_found_mapping(self):
        client = _client(self)
        missing = client.get("/observatory/evolution/EV-nope")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"], "not_found")

    def test_search_bound_mapping(self):
        # GAP-003 (D36 T2): an unparseable search bound is a client error
        # (400 with reason), never a server crash (500).
        client = _client(self)
        client.post("/observatory/events", json=EVENT, headers=WRITER)
        bad_since = client.get("/observatory/search",
                               params={"since": "not-a-timestamp"})
        self.assertEqual(bad_since.status_code, 400)
        self.assertIn("invalid search bound", bad_since.json()["detail"])
        bad_until = client.get("/observatory/search",
                               params={"until": "2026-13-99"})
        self.assertEqual(bad_until.status_code, 400)
        bad_export = client.get("/observatory/export/events",
                                params={"since": "not-a-timestamp"})
        self.assertEqual(bad_export.status_code, 400)
        good = client.get("/observatory/search",
                          params={"since": "2026-01-01T00:00:00+00:00"})
        self.assertEqual(good.status_code, 200)
        plain = client.get("/observatory/search", params={"q": "SUBJ-1"})
        self.assertEqual(plain.status_code, 200)

    def test_command_accept_and_reject(self):
        client = _client(self)
        client.post("/observatory/events", json={
            "source": "test", "category": "governance",
            "type": "authority_updated", "subject_id": "GOVERNANCE",
            "payload": {"authority": {"implementation": "granted"}}},
            headers=WRITER)
        accepted = client.post(
            "/observatory/commands",
            json={"action": "request_implementation",
                  "params": {"target_id": "EV-002"}},
            headers=OPERATOR)
        self.assertEqual(accepted.status_code, 200)
        rejected = client.post(
            "/observatory/commands",
            json={"action": "request_implementation",
                  "params": {"target_id": "EV-002"}},
            headers=OBSERVER)
        self.assertEqual(rejected.status_code, 403)
        unknown = client.post(
            "/observatory/commands",
            json={"action": "start_evolution", "params": {}},
            headers=OPERATOR)
        self.assertEqual(unknown.status_code, 403)

    def test_evidence_lookup(self):
        client = _client(self)
        client.post("/observatory/events", json=dict(
            EVENT, category="evidence", subject_id="E-1",
            payload={"claim": "c", "result": "pass"}), headers=WRITER)
        found = client.get("/observatory/evidence/E-1")
        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.json()["evidence_id"], "E-1")


if __name__ == "__main__":
    unittest.main()
