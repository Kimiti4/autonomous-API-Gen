"""Observatory projection unit + invariant tests (pure functions only).

Includes the never-fabricate regression suite: missing results, empty
streams, and unmeasured metrics must surface as unknown/not_measured,
never as success/zero/green.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from observatory.backend.domain import (
    EpistemicStatus, EventCategory, Severity, new_event)
from observatory.backend import projections as P


def _event(timestamp_minute: int = 0, **overrides):
    base = {"category": EventCategory.RUNTIME, "source": "test",
            "type": "process_started", "subject_id": "SUBJ-1",
            "timestamp": datetime(2026, 1, 1, 0, timestamp_minute,
                                  tzinfo=timezone.utc)}
    base.update(overrides)
    return new_event(**base)


class NeverFabricate(unittest.TestCase):
    def test_missing_result_is_not_ok(self):
        self.assertFalse(P.result_is_ok(None))

    def test_stage_needs_result(self):
        events = [_event(type="requirement_parsed",
                         payload={"note": "no result key"})]
        self.assertFalse(P.stage_done(events, "requirement_parsed"))

    def test_empty_stream_health_unknown(self):
        self.assertEqual(P.derive_runtime_health([]), "unknown")

    def test_empty_stream_status_unknown(self):
        self.assertEqual(P.derive_evolution_status([], []), "unknown")

    def test_unmeasured_metric_marker(self):
        state = P.build_runtime_state([_event()])
        self.assertEqual(state["messages_per_sec"], "not_measured")
        self.assertEqual(state["memory_total"], "not_measured")

    def test_no_events_no_epistemics(self):
        self.assertEqual(P.count_epistemic([]),
                         {"observed": 0, "inferred": 0, "unknown": 0,
                          "contradiction": 0})

    def test_unknown_requirement_returns_none(self):
        self.assertIsNone(P.build_requirement_state("REQ-9", []))
        self.assertIsNone(P.build_capability_state("CAP-9", []))


class Projections(unittest.TestCase):
    def test_runtime_health_green(self):
        state = P.build_runtime_state([_event()])
        self.assertEqual(state["health"], "green")
        self.assertEqual(state["processes"], 1)

    def test_runtime_health_degraded(self):
        events = [_event(), _event(type="process_crashed",
                                   severity=Severity.ERROR, timestamp_minute=1)]
        self.assertEqual(P.build_runtime_state(events)["health"], "degraded")

    def test_pipeline_progress(self):
        events = [_event(type="requirement_parsed",
                         payload={"result": "success"}),
                  _event(type="isr_consulted", payload={"result": "success"},
                         timestamp_minute=1)]
        pipeline = P.build_pipeline(events)
        by_stage = {item["stage"]: item["status"] for item in pipeline}
        self.assertEqual(by_stage["requirement_parsed"], "done")
        self.assertEqual(by_stage["constraints_derived"], "current")

    def test_pipeline_failed(self):
        events = [_event(type="stage_failed",
                         payload={"stage": "candidate_generated"})]
        by_stage = {item["stage"]: item["status"]
                    for item in P.build_pipeline(events)}
        self.assertEqual(by_stage["candidate_generated"], "failed")

    def test_evolution_blocked(self):
        events = [_event(category=EventCategory.EVOLUTION,
                         type="evolution_blocked", subject_id="EV-1")]
        state = P.build_evolution_state("EV-1", events)
        self.assertEqual(state["status"], "blocked")

    def test_decision_vocabulary_closed(self):
        events = [_event(category=EventCategory.EVOLUTION,
                         type="decision_recorded",
                         subject_id="EV-1",
                         payload={"decision": "transcend_now"})]
        state = P.build_evolution_state("EV-1", events)
        self.assertEqual(state["decision"], "recorded")

    def test_decision_known_values(self):
        for event_type, expected in (("evolution_advanced", "advanced"),
                                     ("evolution_held", "held"),
                                     ("evolution_blocked", "blocked")):
            events = [_event(category=EventCategory.EVOLUTION,
                             type=event_type, subject_id="EV-1")]
            state = P.build_evolution_state("EV-1", events)
            self.assertEqual(state["decision"], expected, event_type)

    def test_capability_defaults_unknown(self):
        state = P.build_evolution_state("EV-1", [_event(subject_id="EV-1")])
        self.assertEqual(state["capability_check"]["production"], "unknown")

    def test_epistemic_counts(self):
        events = [
            _event(category=EventCategory.EVIDENCE, subject_id="E-1"),
            _event(category=EventCategory.EVIDENCE, subject_id="E-1",
                   epistemic_status=EpistemicStatus.UNKNOWN,
                   timestamp_minute=1),
            _event(category=EventCategory.RUNTIME, subject_id="E-1",
                   timestamp_minute=2)]
        state = P.build_evolution_state("E-1", events)
        self.assertEqual(state["epistemic_state"]["observed"], 1)
        self.assertEqual(state["epistemic_state"]["unknown"], 1)

    def test_determinism_reordered(self):
        events = [_event(timestamp_minute=2), _event(timestamp_minute=0),
                  _event(timestamp_minute=1)]
        first = P.build_evolution_state("SUBJ-1", events)
        second = P.build_evolution_state("SUBJ-1", list(reversed(events)))
        self.assertEqual(first["status"], second["status"])
        self.assertEqual(first["epistemic_state"], second["epistemic_state"])
        self.assertEqual(
            [item["status"] for item in first["pipeline"]],
            [item["status"] for item in second["pipeline"]])

    def test_governance_defaults(self):
        state = P.build_governance_state([])
        self.assertEqual(state["safe_mode"], "unknown")
        self.assertEqual(state["current_authority"]["production"], "none")
        self.assertEqual(state["command_activity"],
                         {"requested": 0, "accepted": 0, "rejected": 0})

    def test_governance_command_counts(self):
        events = [
            _event(category=EventCategory.GOVERNANCE, type="command_requested"),
            _event(category=EventCategory.GOVERNANCE, type="command_rejected",
                   timestamp_minute=1)]
        state = P.build_governance_state(events)
        self.assertEqual(state["command_activity"]["requested"], 1)
        self.assertEqual(state["command_activity"]["rejected"], 1)

    def test_contradiction_listing(self):
        events = [_event(category=EventCategory.EVIDENCE, subject_id="E-1",
                         epistemic_status=EpistemicStatus.CONTRADICTION)]
        self.assertEqual(P.derive_contradictions(events), ["E-1"])


if __name__ == "__main__":
    unittest.main()
