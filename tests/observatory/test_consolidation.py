"""Consolidation tests: search, export, audit bundles (all read-only)."""
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
    base = {"source": "test", "category": "runtime",
            "type": "process_started", "subject_id": "PROC-1",
            "payload": {"summary": "AgencyLoop started"}}
    base.update(overrides)
    response = client.post("/observatory/events", json=base, headers=WRITER)
    assert response.status_code == 200, response.text
    return response


class Search(unittest.TestCase):
    def test_empty_store_empty_results(self):
        client = _client(self)
        response = client.get("/observatory/search")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_subject_text_match(self):
        client = _client(self)
        _emit(client)
        _emit(client, subject_id="OTHER-1", type="metric",
              payload={"summary": "unrelated"})
        results = client.get("/observatory/search",
                             params={"q": "PROC-1"}).json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["subject_id"], "PROC-1")

    def test_type_and_payload_text_match(self):
        client = _client(self)
        _emit(client)
        by_type = client.get("/observatory/search",
                             params={"q": "process_started"}).json()
        self.assertEqual(len(by_type), 1)
        by_payload = client.get("/observatory/search",
                                params={"q": "AgencyLoop started"}).json()
        self.assertEqual(len(by_payload), 1)

    def test_category_filter(self):
        client = _client(self)
        _emit(client)
        _emit(client, category="evidence", type="experiment_result",
              subject_id="E-1",
              payload={"claim": "c", "result": "pass"})
        runtime = client.get("/observatory/search",
                             params={"categories": "runtime"}).json()
        self.assertTrue(all(r["category"] == "runtime" for r in runtime))
        evidence = client.get("/observatory/search",
                              params={"categories": "evidence"}).json()
        self.assertEqual(len(evidence), 1)

    def test_severity_filter(self):
        client = _client(self)
        _emit(client)
        response = client.get("/observatory/search",
                              params={"severities": "error"})
        self.assertEqual(response.json(), [])

    def test_epistemic_filter(self):
        client = _client(self)
        _emit(client)
        response = client.get(
            "/observatory/search", params={"epistemic_statuses": "observed"})
        self.assertEqual(len(response.json()), 1)
        missing = client.get(
            "/observatory/search", params={"epistemic_statuses": "unknown"})
        self.assertEqual(missing.json(), [])

    def test_time_window(self):
        client = _client(self)
        _emit(client)
        inside = client.get("/observatory/search", params={
            "since": "2020-01-01T00:00:00+00:00",
            "until": "2030-01-01T00:00:00+00:00"}).json()
        self.assertEqual(len(inside), 1)
        outside = client.get("/observatory/search", params={
            "since": "2030-01-01T00:00:00+00:00"}).json()
        self.assertEqual(outside, [])

    def test_limit_respected(self):
        client = _client(self)
        for index in range(3):
            _emit(client, subject_id=f"P-{index}")
        results = client.get("/observatory/search",
                             params={"limit": 2}).json()
        self.assertEqual(len(results), 2)

    def test_result_shape_metadata_only(self):
        client = _client(self)
        _emit(client, payload={"summary": "x", "secret": "y"})
        result = client.get("/observatory/search").json()[0]
        self.assertEqual(
            sorted(result),
            ["category", "entity_type", "epistemic_status", "event_id",
             "severity", "source", "subject_id", "summary", "timestamp",
             "type"])
        self.assertNotIn("payload", result)


class Export(unittest.TestCase):
    def test_json_export(self):
        client = _client(self)
        _emit(client)
        response = client.get("/observatory/export/events",
                              params={"format": "json"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_csv_export(self):
        client = _client(self)
        _emit(client)
        response = client.get("/observatory/export/events",
                              params={"format": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        lines = response.text.strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("event_id,"))
        self.assertNotIn("payload", lines[0])

    def test_bad_format(self):
        client = _client(self)
        response = client.get("/observatory/export/events",
                              params={"format": "xml"})
        self.assertEqual(response.status_code, 400)

    def test_export_respects_filters(self):
        client = _client(self)
        _emit(client)
        _emit(client, subject_id="OTHER-1", type="metric",
              payload={"summary": "other"})
        filtered = client.get("/observatory/export/events",
                              params={"q": "PROC-1", "format": "json"}).json()
        self.assertEqual(len(filtered), 1)


class AuditBundle(unittest.TestCase):
    def test_bundle_404(self):
        client = _client(self)
        missing = client.get("/observatory/audit-bundle/EXP-nope")
        self.assertEqual(missing.status_code, 404)

    def test_bundle_content(self):
        client = _client(self)
        _emit(client, category="evolution", type="experiment_proposed",
              subject_id="EXP-1",
              payload={"experiment_id": "EXP-1",
                       "summary": "Proposed"})
        _emit(client, category="evidence", type="experiment_result",
              subject_id="EXP-1",
              payload={"experiment_id": "EXP-1", "name": "filter",
                       "observed": "ok"})
        bundle = client.get("/observatory/audit-bundle/EXP-1").json()
        self.assertEqual(bundle["bundle_version"],
                         "observatory-audit-bundle-v1")
        self.assertEqual(bundle["subject_id"], "EXP-1")
        self.assertIn("generated_at", bundle)
        self.assertEqual(bundle["links"]["provenance"], "/provenance/EXP-1")
        self.assertEqual(bundle["links"]["view"], "/experiments/EXP-1")
        audit = bundle["provenance_audit"]
        self.assertGreaterEqual(len(audit["hash_chain"]), 1)
        self.assertIn("timeline", audit)

    def test_bundle_links_per_entity(self):
        client = _client(self)
        _emit(client, category="knowledge", type="knowledge_recorded",
              subject_id="KNOW-A",
              payload={"knowledge_id": "KNOW-A", "statement": "s"})
        bundle = client.get("/observatory/audit-bundle/KNOW-A").json()
        self.assertEqual(bundle["links"]["view"], "/knowledge/KNOW-A")

    def test_bundle_unknown_entity_links_provenance(self):
        client = _client(self)
        _emit(client)
        bundle = client.get("/observatory/audit-bundle/PROC-1").json()
        self.assertEqual(bundle["links"]["view"], "/provenance/PROC-1")


class ConsoleBoundary(unittest.TestCase):
    def test_console_page_render_only(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parents[2] / "observatory"
               / "frontend" / "app" / "console" / "page.tsx").read_text(
                   encoding="utf-8")
        # Export links are plain anchors (GET downloads), never fetches.
        self.assertNotIn("/observatory/commands", src)
        self.assertNotIn("method: \"POST\"", src)
        # Saved traces stay in browser local storage, never posted anywhere,
        # and are labeled as operator conveniences, not system evidence.
        self.assertIn("localStorage", src)
        lowered = src.lower()
        self.assertIn("stored locally in the browser", lowered)
        self.assertIn("not authoritative system evidence", lowered)


if __name__ == "__main__":
    unittest.main()
