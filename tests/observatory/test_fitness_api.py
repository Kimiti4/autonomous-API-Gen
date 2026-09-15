"""Fitness API tests: overview/detail contract over live TestClient."""
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
            "type": "fitness_objective_defined", "subject_id": "FIT-1",
            "payload": {"fitness_id": "FIT-1",
                        "objective": "Evaluate priority."}}
    base.update(overrides)
    response = client.post("/observatory/events", json=base, headers=WRITER)
    assert response.status_code == 200, response.text
    return response


class FitnessApi(unittest.TestCase):
    def test_overview_empty(self):
        client = _client(self)
        response = client.get("/observatory/fitness")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_lifecycle_populates(self):
        client = _client(self)
        _emit(client)
        _emit(client, type="metric_defined", subject_id="METRIC-A",
              payload={"fitness_id": "FIT-1", "metric_id": "METRIC-A",
                       "name": "Coverage"})
        _emit(client, category="evidence", type="fitness_measurement",
              subject_id="METRIC-A",
              payload={"fitness_id": "FIT-1", "metric_id": "METRIC-A",
                       "value": 75, "unit": "percent"})
        _emit(client, category="evidence", type="fitness_baseline",
              subject_id="METRIC-A",
              payload={"fitness_id": "FIT-1", "metric_id": "METRIC-A",
                       "baseline": 50, "unit": "percent"})
        overview = client.get("/observatory/fitness").json()
        self.assertEqual(len(overview), 1)
        item = overview[0]
        self.assertEqual(item["status"], "measured")
        self.assertEqual(item["metric_count"], 1)
        self.assertEqual(item["measurement_count"], 1)
        self.assertEqual(item["baseline_count"], 1)
        self.assertEqual(item["pareto_state"], "unknown")

    def test_detail_404(self):
        client = _client(self)
        missing = client.get("/observatory/fitness/FIT-nope")
        self.assertEqual(missing.status_code, 404)

    def test_detail_metric_delta(self):
        client = _client(self)
        _emit(client)
        _emit(client, category="evidence", type="fitness_measurement",
              subject_id="METRIC-A",
              payload={"fitness_id": "FIT-1", "metric_id": "METRIC-A",
                       "value": 75, "unit": "percent"})
        _emit(client, category="evidence", type="fitness_baseline",
              subject_id="METRIC-A",
              payload={"fitness_id": "FIT-1", "metric_id": "METRIC-A",
                       "baseline": 50, "unit": "percent"})
        detail = client.get("/observatory/fitness/FIT-1").json()
        self.assertEqual(len(detail["metrics"]), 1)
        metric = detail["metrics"][0]
        self.assertEqual(metric["latest_value"], 75)
        self.assertEqual(metric["baseline_value"], 50)
        self.assertEqual(metric["delta_vs_baseline"], 25)
        self.assertEqual(metric["status"], "measured")

    def test_missing_metric_shown_missing(self):
        client = _client(self)
        _emit(client)
        _emit(client, type="metric_defined", subject_id="METRIC-B",
              payload={"fitness_id": "FIT-1", "metric_id": "METRIC-B",
                       "name": "Latency"})
        detail = client.get("/observatory/fitness/FIT-1").json()
        metric = next(m for m in detail["metrics"]
                      if m["metric_id"] == "METRIC-B")
        self.assertEqual(metric["status"], "missing")
        self.assertIsNone(metric["latest_value"])
        self.assertIsNone(metric["delta_vs_baseline"])

    def test_contradicted_metric_shown(self):
        client = _client(self)
        _emit(client)
        _emit(client, category="evidence", type="fitness_measurement",
              subject_id="METRIC-A",
              payload={"fitness_id": "FIT-1", "metric_id": "METRIC-A",
                       "value": 75},
              epistemic_status="contradiction")
        detail = client.get("/observatory/fitness/FIT-1").json()
        metric = next(m for m in detail["metrics"]
                      if m["metric_id"] == "METRIC-A")
        self.assertEqual(metric["status"], "contradicted")
        self.assertEqual(len(detail["contradictions"]), 1)


if __name__ == "__main__":
    unittest.main()
