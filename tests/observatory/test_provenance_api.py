"""Provenance API tests: overview/audit contract over live TestClient."""
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
                        "fitness_id": "FIT-1",
                        "summary": "Proposed"}}
    base.update(overrides)
    response = client.post("/observatory/events", json=base, headers=WRITER)
    assert response.status_code == 200, response.text
    return response


class ProvenanceApi(unittest.TestCase):
    def test_overview_empty(self):
        client = _client(self)
        response = client.get("/observatory/provenance")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_subjects_from_events(self):
        client = _client(self)
        _emit(client)
        _emit(client, subject_id="EXP-2",
              payload={"experiment_id": "EXP-2"})
        overview = client.get("/observatory/provenance").json()
        self.assertEqual(len(overview), 2)
        by_id = {item["subject_id"]: item for item in overview}
        self.assertEqual(by_id["EXP-1"]["entity_type"], "evolution")
        self.assertEqual(by_id["EXP-1"]["event_count"], 1)
        self.assertGreaterEqual(by_id["EXP-1"]["reference_count"], 1)

    def test_filter_note(self):
        # Filtering is a presentation concern; the API returns the full
        # inventory newest-first for the UI to filter client-side.
        client = _client(self)
        _emit(client)
        overview = client.get("/observatory/provenance").json()
        self.assertEqual(overview[0]["subject_id"], "EXP-1")

    def test_audit_404(self):
        client = _client(self)
        missing = client.get("/observatory/provenance/EXP-nope")
        self.assertEqual(missing.status_code, 404)

    def test_audit_sections(self):
        client = _client(self)
        _emit(client)
        _emit(client, category="evidence", type="experiment_result",
              payload={"experiment_id": "EXP-1", "name": "filter",
                       "observed": "ok"},
              evidence_refs=["EVD-1"])
        _emit(client, category="governance", type="command_rejected",
              subject_id="OTHER",
              payload={"experiment_id": "EXP-1", "reason": "blocked"})
        audit = client.get("/observatory/provenance/EXP-1").json()
        self.assertEqual(audit["direct_event_count"], 2)
        self.assertEqual(audit["related_event_count"], 1)
        chain = audit["hash_chain"]
        self.assertEqual(len(chain), 2)
        self.assertIsNone(chain[0]["previous_event_hash"])
        self.assertEqual(chain[1]["previous_event_hash"],
                         chain[0]["event_hash"])
        self.assertEqual(len(audit["warnings"]), 1)
        self.assertEqual(len(audit["governance_events"]), 1)
        self.assertEqual(len(audit["timeline"]), 3)
        self.assertIn("EVD-1", audit["evidence_refs"])
        relations = {(e["source"], e["target"]) for e in audit["edges"]}
        self.assertIn(("EXP-1", "FIT-1"), relations)
        self.assertIn(("OTHER", "EXP-1"), relations)

    def test_warnings_for_rejected_authorizations(self):
        client = _client(self)
        _emit(client, category="governance", type="authorization_rejected",
              subject_id="AUTH-1",
              payload={"reason": "insufficient clearance"})
        audit = client.get("/observatory/provenance/AUTH-1").json()
        self.assertEqual(len(audit["warnings"]), 1)
        self.assertEqual(audit["warnings"][0]["type"],
                         "authorization_rejected")

    def test_warnings_for_blocked_decisions(self):
        client = _client(self)
        _emit(client, category="governance", type="decision_blocked",
              subject_id="DEC-1",
              payload={"reason": "hold"})
        audit = client.get("/observatory/provenance/DEC-1").json()
        self.assertEqual(len(audit["warnings"]), 1)

    def test_warnings_for_rejected_authorizations(self):
        client = _client(self)
        _emit(client, category="governance", type="authorization_rejected",
              subject_id="AUTH-1",
              payload={"reason": "insufficient clearance"})
        audit = client.get("/observatory/provenance/AUTH-1").json()
        self.assertEqual(len(audit["warnings"]), 1)
        self.assertEqual(audit["warnings"][0]["type"],
                         "authorization_rejected")

    def test_warnings_for_safe_mode(self):
        client = _client(self)
        _emit(client, category="governance", type="safe_mode_enabled",
              subject_id="GOVERNANCE", payload={})
        audit = client.get("/observatory/provenance/GOVERNANCE").json()
        self.assertEqual(len(audit["warnings"]), 1)

    def test_warnings_for_contradictions(self):
        client = _client(self)
        _emit(client, category="evidence", type="experiment_result",
              subject_id="EXP-1",
              payload={"experiment_id": "EXP-1"},
              epistemic_status="contradiction")
        audit = client.get("/observatory/provenance/EXP-1").json()
        self.assertEqual(len(audit["warnings"]), 1)
        self.assertEqual(audit["warnings"][0]["type"], "contradiction")

    def test_classification_stable(self):
        client = _client(self)
        _emit(client)
        first = client.get("/observatory/provenance/EXP-1").json()
        _emit(client, type="experiment_authorized",
              payload={"experiment_id": "EXP-1"})
        second = client.get("/observatory/provenance/EXP-1").json()
        self.assertEqual(first["entity_type"], second["entity_type"])
        self.assertEqual(first["entity_type"], "evolution")

    def test_actors_render(self):
        client = _client(self)
        _emit(client)
        audit = client.get("/observatory/provenance/EXP-1").json()
        self.assertIn("test", audit["actors"])

    def test_timeline_newest_first(self):
        client = _client(self)
        _emit(client)
        audit = client.get("/observatory/provenance/EXP-1").json()
        timestamps = [t["timestamp"] for t in audit["timeline"]]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))


if __name__ == "__main__":
    unittest.main()
