"""Observatory domain unit tests: envelope, constructors, identity."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from observatory.backend.domain import (
    EpistemicStatus, EventCategory, Severity, canonical_json,
    event_from_input, event_hash, generate_event_id, new_event,
    new_evidence_event, new_governance_event, EventInput)


def _event(**overrides):
    base = {"category": EventCategory.RUNTIME, "source": "test",
            "type": "process_started", "subject_id": "SUBJ-1"}
    base.update(overrides)
    return new_event(**base)


class Domain(unittest.TestCase):
    def test_required_fields(self):
        with self.assertRaises(ValueError):
            new_event(category=EventCategory.RUNTIME, source="",
                      type="t", subject_id="s")
        with self.assertRaises(ValueError):
            new_event(category=EventCategory.RUNTIME, source="s",
                      type="", subject_id="s")

    def test_deterministic_id(self):
        timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        first = generate_event_id(
            category=EventCategory.EVIDENCE, source="s", type="t",
            subject_id="x", payload={"a": 1}, timestamp=timestamp)
        second = generate_event_id(
            category=EventCategory.EVIDENCE, source="s", type="t",
            subject_id="x", payload={"a": 1}, timestamp=timestamp)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("evt-evidence-"))

    def test_event_hash_stable(self):
        event = _event(id="evt-1",
                       timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(event_hash(event), event_hash(event))
        self.assertEqual(len(event_hash(event)), 64)

    def test_canonical_json_keys_sorted(self):
        self.assertEqual(canonical_json({"b": 1, "a": 2}), '{"a":2,"b":1}')

    def test_evidence_requires_claim_result(self):
        with self.assertRaises(ValueError):
            new_evidence_event(source="s", subject_id="x", claim="",
                               result="pass")
        with self.assertRaises(ValueError):
            new_evidence_event(source="s", subject_id="x", claim="c",
                               result=None)

    def test_governance_rejection_needs_reason(self):
        with self.assertRaises(ValueError):
            new_governance_event(source="s", type="command_rejected")

    def test_from_input_defaults(self):
        event = event_from_input(EventInput(
            source="s", category=EventCategory.RUNTIME, type="t",
            subject_id="x"))
        self.assertEqual(event.epistemic_status, EpistemicStatus.OBSERVED)
        self.assertEqual(event.severity, Severity.INFO)
        self.assertTrue(event.id)
        self.assertIsNotNone(event.timestamp)


if __name__ == "__main__":
    unittest.main()
