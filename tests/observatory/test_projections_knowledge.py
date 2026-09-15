"""Knowledge projection unit tests (pure functions, temp-free)."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from observatory.backend.domain import (
    EpistemicStatus, EventCategory, new_event)
from observatory.backend.projections_knowledge import (
    build_knowledge_memory, build_knowledge_overview,
    extract_knowledge_subject_id)


def _event(**overrides):
    base = {"category": EventCategory.KNOWLEDGE, "source": "test",
            "type": "knowledge_recorded", "subject_id": "KNOW-A",
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    base.update(overrides)
    return new_event(**base)


class Extraction(unittest.TestCase):
    def test_payload_keys_win(self):
        event = _event(subject_id="OTHER",
                       payload={"memory_id": "MEM-1"})
        self.assertEqual(extract_knowledge_subject_id(event), "MEM-1")

    def test_category_fallback(self):
        self.assertEqual(
            extract_knowledge_subject_id(_event(subject_id="KNOW-A")),
            "KNOW-A")

    def test_non_knowledge_ignored(self):
        event = new_event(
            category=EventCategory.RUNTIME, source="test",
            type="process_started", subject_id="PROC-1",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertIsNone(extract_knowledge_subject_id(event))

    def test_prefix_subjects(self):
        event = new_event(
            category=EventCategory.RUNTIME, source="test",
            type="memory_updated", subject_id="MEM-X",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(extract_knowledge_subject_id(event), "MEM-X")


class Overview(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(build_knowledge_overview([]), [])

    def test_subjects_grouped_sorted(self):
        events = [_event(subject_id="KNOW-B",
                         payload={"statement": "second"}),
                  _event(subject_id="KNOW-A",
                         payload={"statement": "first"})]
        overview = build_knowledge_overview(events)
        self.assertEqual([item["subject_id"] for item in overview],
                         ["KNOW-A", "KNOW-B"])
        self.assertEqual(overview[0]["epistemic_state"]["observed"], 1)

    def test_unrelated_excluded(self):
        runtime = new_event(
            category=EventCategory.RUNTIME, source="test",
            type="process_started", subject_id="PROC-1",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(build_knowledge_overview([runtime]), [])


class Memory(unittest.TestCase):
    def _events(self):
        return [
            _event(payload={"statement": "Priority filtering worked.",
                            "knowledge_id": "KNOW-P"}),
            _event(type="unknown_recorded", subject_id="KNOW-P",
                   epistemic_status=EpistemicStatus.UNKNOWN,
                   payload={"knowledge_id": "KNOW-P",
                            "unknown_id": "UNKNOWN-1",
                            "question": "UI proof?",
                            "reason": "no UI evidence"}),
            _event(type="memory_updated", subject_id="KNOW-P",
                   payload={"knowledge_id": "KNOW-P",
                            "summary": "cycle closed",
                            "memory": {"cycle": 1}}),
        ]

    def test_missing_returns_none(self):
        self.assertIsNone(build_knowledge_memory("KNOW-nope", self._events()))

    def test_sections(self):
        memory = build_knowledge_memory("KNOW-P", self._events())
        assert memory is not None
        # Both the statement record and the knowledge-category memory
        # record are fact-eligible per the classification rule.
        self.assertEqual(len(memory["facts"]), 2)
        self.assertEqual(memory["facts"][0]["statement"],
                         "Priority filtering worked.")
        self.assertEqual(len(memory["unknowns"]), 1)
        self.assertEqual(memory["unknowns"][0]["unknown_id"], "UNKNOWN-1")
        self.assertEqual(len(memory["memories"]), 1)
        self.assertEqual(memory["memories"][0]["summary"], "cycle closed")
        self.assertEqual(memory["contradictions"], [])
        self.assertEqual(len(memory["timeline"]), 3)

    def test_contradiction_section(self):
        events = self._events() + [
            _event(type="contradiction_recorded", subject_id="KNOW-P",
                   epistemic_status=EpistemicStatus.CONTRADICTION,
                   payload={"knowledge_id": "KNOW-P",
                            "contradiction_id": "CONTRA-1",
                            "statement": "Conflict.",
                            "left_evidence_id": "E-1",
                            "right_evidence_id": "E-2"})]
        memory = build_knowledge_memory("KNOW-P", events)
        assert memory is not None
        self.assertEqual(len(memory["contradictions"]), 1)
        self.assertEqual(
            memory["contradictions"][0]["contradiction_id"], "CONTRA-1")


if __name__ == "__main__":
    unittest.main()
