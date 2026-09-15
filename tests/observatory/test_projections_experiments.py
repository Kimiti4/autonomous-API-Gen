"""Experiment projection unit tests (pure functions)."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from observatory.backend.domain import (
    EpistemicStatus, EventCategory, new_event)
from observatory.backend.projections_experiments import (
    build_experiment_detail,
    build_experiments_overview,
    derive_authorization_state,
    derive_experiment_status,
    derive_reproducibility_state,
    extract_experiment_id,
)


def _event(**overrides):
    base = {"category": EventCategory.EVOLUTION, "source": "test",
            "type": "experiment_proposed", "subject_id": "EXP-1",
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    base.update(overrides)
    return new_event(**base)


class Extraction(unittest.TestCase):
    def test_payload_keys_win(self):
        event = _event(subject_id="OTHER",
                       payload={"trial_id": "TRIAL-7"})
        self.assertEqual(extract_experiment_id(event), "TRIAL-7")

    def test_type_prefix(self):
        event = _event(type="trial_started", subject_id="whatever")
        self.assertEqual(extract_experiment_id(event), "whatever")

    def test_exp_prefix(self):
        event = _event(type="process_started", subject_id="EXP-9")
        self.assertEqual(extract_experiment_id(event), "EXP-9")

    def test_unrelated_none(self):
        event = _event(type="process_started", subject_id="PROC-1")
        self.assertIsNone(extract_experiment_id(event))


class StatusDerivation(unittest.TestCase):
    def test_explicit_status_wins(self):
        events = [_event(payload={"status": "custom"})]
        self.assertEqual(derive_experiment_status(events), "custom")

    def test_lifecycle_order(self):
        self.assertEqual(
            derive_experiment_status([_event(type="experiment_started")]),
            "running")
        self.assertEqual(
            derive_experiment_status([_event(type="experiment_completed")]),
            "completed")
        self.assertEqual(
            derive_experiment_status([_event(type="experiment_failed")]),
            "failed")

    def test_empty_unknown(self):
        self.assertEqual(derive_experiment_status([]), "unknown")

    def test_authorization_never_defaults_authorized(self):
        self.assertEqual(derive_authorization_state([]), "unknown")
        self.assertEqual(
            derive_authorization_state([_event()]), "not_authorized")
        self.assertEqual(
            derive_authorization_state(
                [_event(type="experiment_authorized")]), "authorized")
        self.assertEqual(
            derive_authorization_state(
                [_event(type="experiment_authorized"),
                 _event(type="experiment_rejected")]), "rejected")

    def test_reproducibility_unknown_unless_recorded(self):
        self.assertEqual(derive_reproducibility_state([]), "unknown")
        self.assertEqual(
            derive_reproducibility_state([_event()]), "unknown")
        self.assertEqual(
            derive_reproducibility_state(
                [_event(payload={"reproducibility": True})]), "verified")
        self.assertEqual(
            derive_reproducibility_state(
                [_event(payload={"reproducibility": "REPRODUCED"})]),
            "verified")


class OverviewDetail(unittest.TestCase):
    def _lifecycle(self):
        return [
            _event(payload={"hypothesis": "Filtering works.",
                            "experiment_id": "EXP-1",
                            "fixture": "loopback",
                            "environment": "validation"}),
            _event(type="experiment_authorized", subject_id="EXP-1",
                   payload={"experiment_id": "EXP-1"}),
            _event(type="experiment_started", subject_id="EXP-1",
                   payload={"experiment_id": "EXP-1",
                            "run_id": "RUN-1"}),
            _event(type="experiment_result", subject_id="EXP-1",
                   category=EventCategory.EVIDENCE,
                   payload={"experiment_id": "EXP-1", "name": "filter-high",
                            "expected": "HIGH only",
                            "observed": "HIGH only", "passed": True}),
            _event(type="experiment_completed", subject_id="EXP-1",
                   payload={"experiment_id": "EXP-1", "status": "completed"}),
        ]

    def test_overview_empty(self):
        self.assertEqual(build_experiments_overview([]), [])

    def test_overview_populated(self):
        overview = build_experiments_overview(self._lifecycle())
        self.assertEqual(len(overview), 1)
        item = overview[0]
        self.assertEqual(item["experiment_id"], "EXP-1")
        self.assertEqual(item["status"], "completed")
        self.assertEqual(item["authorization_state"], "authorized")
        self.assertEqual(item["reproducibility"], "unknown")
        self.assertEqual(item["hypothesis"], "Filtering works.")
        self.assertEqual(item["results_count"], 1)

    def test_detail_sections(self):
        detail = build_experiment_detail("EXP-1", self._lifecycle())
        assert detail is not None
        self.assertEqual(detail["run_id"], "RUN-1")
        self.assertEqual(len(detail["results"]), 1)
        self.assertTrue(detail["results"][0]["passed"])
        self.assertEqual(detail["unknowns"], [])
        self.assertEqual(detail["contradictions"], [])
        self.assertEqual(
            [t["type"] for t in detail["timeline"]],
            ["experiment_completed", "experiment_result",
             "experiment_started", "experiment_authorized",
             "experiment_proposed"])

    def test_detail_missing_none(self):
        self.assertIsNone(build_experiment_detail("EXP-nope", self._lifecycle()))

    def test_unknowns_preserved(self):
        events = self._lifecycle() + [_event(
            type="unknown_recorded", subject_id="EXP-1",
            epistemic_status=EpistemicStatus.UNKNOWN,
            payload={"experiment_id": "EXP-1", "unknown_id": "U-9",
                     "question": "Scale?"})]
        detail = build_experiment_detail("EXP-1", events)
        assert detail is not None
        self.assertEqual(len(detail["unknowns"]), 1)
        self.assertEqual(detail["unknowns"][0]["unknown_id"], "U-9")


if __name__ == "__main__":
    unittest.main()
