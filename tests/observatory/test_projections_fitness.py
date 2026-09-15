"""Fitness projection unit tests (pure functions)."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from observatory.backend.domain import (
    EpistemicStatus, EventCategory, new_event)
from observatory.backend.projections_fitness import (
    build_fitness_detail,
    build_fitness_metrics,
    build_fitness_overview,
    derive_fitness_status,
    derive_pareto_state,
    extract_fitness_id,
    extract_metric_id,
)


def _event(**overrides):
    base = {"category": EventCategory.EVOLUTION, "source": "test",
            "type": "fitness_objective_defined", "subject_id": "FIT-1",
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    base.update(overrides)
    return new_event(**base)


class Extraction(unittest.TestCase):
    def test_payload_keys_win(self):
        event = _event(subject_id="OTHER",
                       payload={"evaluation_id": "EVAL-3"})
        self.assertEqual(extract_fitness_id(event), "EVAL-3")

    def test_type_prefix(self):
        event = _event(type="pareto_observed", subject_id="whatever")
        self.assertEqual(extract_fitness_id(event), "whatever")

    def test_fit_prefix(self):
        event = _event(type="process_started", subject_id="FIT-9")
        self.assertEqual(extract_fitness_id(event), "FIT-9")

    def test_unrelated_none(self):
        event = _event(type="process_started", subject_id="PROC-1")
        self.assertIsNone(extract_fitness_id(event))

    def test_metric_extraction(self):
        self.assertEqual(
            extract_metric_id(_event(payload={"metric_id": "METRIC-A"})),
            "METRIC-A")
        self.assertEqual(
            extract_metric_id(_event(type="metric_defined",
                                     subject_id="METRIC-B")),
            "METRIC-B")
        self.assertIsNone(extract_metric_id(_event()))


class StatusDerivation(unittest.TestCase):
    def test_explicit_status_wins(self):
        events = [_event(payload={"status": "custom"})]
        self.assertEqual(derive_fitness_status(events), "custom")

    def test_lifecycle_order(self):
        self.assertEqual(
            derive_fitness_status([_event(type="fitness_measurement")]),
            "measured")
        self.assertEqual(
            derive_fitness_status([_event(type="fitness_evaluation")]),
            "evaluated")
        self.assertEqual(
            derive_fitness_status([_event(type="fitness_failed")]),
            "failed")

    def test_empty_unknown(self):
        self.assertEqual(derive_fitness_status([]), "unknown")

    def test_pareto_unknown_unless_recorded(self):
        self.assertEqual(derive_pareto_state([]), "unknown")
        self.assertEqual(derive_pareto_state([_event()]), "unknown")
        self.assertEqual(
            derive_pareto_state([_event(type="pareto_observed",
                                       payload={"pareto_state": "non_dominated"})]),
            "non_dominated")


class Metrics(unittest.TestCase):
    def _measured(self, **overrides):
        params = {"category": EventCategory.EVIDENCE, "source": "test",
                  "type": "fitness_measurement", "subject_id": "METRIC-A",
                  "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
                  "payload": {"metric_id": "METRIC-A", "value": 75,
                              "unit": "percent"}}
        params.update(overrides)
        return new_event(**params)

    def test_latest_baseline_delta(self):
        baseline = _event(
            category=EventCategory.EVIDENCE, type="fitness_baseline",
            subject_id="METRIC-A",
            payload={"metric_id": "METRIC-A", "baseline": 50,
                     "unit": "percent"})
        measurement = self._measured()
        metrics = build_fitness_metrics([baseline, measurement])
        self.assertEqual(len(metrics), 1)
        metric = metrics[0]
        self.assertEqual(metric["latest_value"], 75)
        self.assertEqual(metric["baseline_value"], 50)
        self.assertEqual(metric["delta_vs_baseline"], 25)
        self.assertEqual(metric["status"], "measured")

    def test_delta_absent_without_numbers(self):
        measurement = self._measured(
            payload={"metric_id": "METRIC-A", "value": "high"})
        metrics = build_fitness_metrics([measurement])
        self.assertIsNone(metrics[0]["delta_vs_baseline"])

    def test_missing_metric_status(self):
        defined = _event(type="metric_defined", subject_id="METRIC-B",
                         payload={"metric_id": "METRIC-B", "name": "Latency"})
        metrics = build_fitness_metrics([defined])
        self.assertEqual(metrics[0]["status"], "missing")
        self.assertIsNone(metrics[0]["latest_value"])

    def test_contradicted_metric(self):
        measurement = self._measured()
        conflict = self._measured(
            epistemic_status=EpistemicStatus.CONTRADICTION)
        metrics = build_fitness_metrics([measurement, conflict])
        self.assertEqual(metrics[0]["status"], "contradicted")


class OverviewDetail(unittest.TestCase):
    def _lifecycle(self):
        return [
            _event(payload={"fitness_id": "FIT-1",
                            "objective": "Evaluate priority.",
                            "scope": ["validation"]}),
            _event(type="metric_defined", subject_id="METRIC-A",
                   payload={"fitness_id": "FIT-1", "metric_id": "METRIC-A",
                            "name": "Coverage"}),
            _event(type="fitness_measurement", subject_id="METRIC-A",
                   category=EventCategory.EVIDENCE,
                   payload={"fitness_id": "FIT-1", "metric_id": "METRIC-A",
                            "value": 75}),
        ]

    def test_overview_empty(self):
        self.assertEqual(build_fitness_overview([]), [])

    def test_overview_populated(self):
        overview = build_fitness_overview(self._lifecycle())
        self.assertEqual(len(overview), 1)
        item = overview[0]
        self.assertEqual(item["fitness_id"], "FIT-1")
        self.assertEqual(item["status"], "measured")
        self.assertEqual(item["metric_count"], 1)
        self.assertEqual(item["measurement_count"], 1)
        self.assertEqual(item["pareto_state"], "unknown")

    def test_detail_sections(self):
        detail = build_fitness_detail("FIT-1", self._lifecycle())
        assert detail is not None
        self.assertEqual(detail["objective"], "Evaluate priority.")
        self.assertEqual(len(detail["metrics"]), 1)
        self.assertEqual(detail["metrics"][0]["latest_value"], 75)
        self.assertEqual(detail["unknowns"], [])
        self.assertEqual(detail["contradictions"], [])
        self.assertEqual(len(detail["timeline"]), 3)

    def test_detail_missing_none(self):
        self.assertIsNone(build_fitness_detail("FIT-nope", self._lifecycle()))

    def test_unknowns_preserved(self):
        events = self._lifecycle() + [_event(
            type="unknown_recorded", subject_id="FIT-1",
            epistemic_status=EpistemicStatus.UNKNOWN,
            payload={"fitness_id": "FIT-1", "unknown_id": "U-5",
                     "question": "Scale?"})]
        detail = build_fitness_detail("FIT-1", events)
        assert detail is not None
        self.assertEqual(len(detail["unknowns"]), 1)


if __name__ == "__main__":
    unittest.main()
