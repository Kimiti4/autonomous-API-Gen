"""Provenance projection unit tests (pure functions)."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from observatory.backend.domain import (
    EpistemicStatus, EventCategory, Severity, event_hash, new_event)
from observatory.backend.projections_provenance import (
    build_actors,
    build_integrity_warnings,
    build_provenance_audit,
    build_provenance_overview,
    classify_entity,
    extract_references,
)


def _event(**overrides):
    base = {"category": EventCategory.EVOLUTION, "source": "test",
            "type": "experiment_proposed", "subject_id": "EXP-1",
            "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc)}
    base.update(overrides)
    return new_event(**base)


class References(unittest.TestCase):
    def test_scalar_and_list_fields(self):
        event = _event(payload={"experiment_id": "EXP-1",
                                "fitness_links": ["FIT-A", "FIT-B"],
                                "evidence_refs": ["EVD-1"]})
        refs = {(r["target"], r["relation"]) for r in extract_references(event)}
        self.assertIn(("EXP-1", "experiment"), refs)
        self.assertIn(("FIT-A", "fitness"), refs)
        self.assertIn(("FIT-B", "fitness"), refs)
        self.assertIn(("EVD-1", "evidence"), refs)

    def test_deduplication(self):
        event = _event(payload={"experiment_id": "EXP-1"},
                       evidence_refs=["EXP-1"])
        targets = [r["target"] for r in extract_references(event)]
        self.assertEqual(len(targets), len(set(
            (r["target"], r["relation"], r["field"])
            for r in extract_references(event))))

    def test_dict_items_resolve_ids(self):
        event = _event(payload={"candidates": [{"candidate_id": "CAND-1"},
                                               {"id": "CAND-2"}]})
        targets = {r["target"] for r in extract_references(event)}
        self.assertEqual(targets, {"CAND-1", "CAND-2"})

    def test_empty(self):
        self.assertEqual(extract_references(_event()), [])


class Classification(unittest.TestCase):
    def test_category_precedence(self):
        events = [_event(category=EventCategory.RUNTIME, subject_id="X"),
                  _event(category=EventCategory.GOVERNANCE, subject_id="X")]
        grouped = {"X": events}
        self.assertEqual(classify_entity("X", grouped), "governance")

    def test_prefix_fallback(self):
        self.assertEqual(classify_entity("REQ-1", {}), "requirement")
        self.assertEqual(classify_entity("GEN-1", {}), "genome")
        self.assertEqual(classify_entity("DEC-1", {}), "decision")
        self.assertEqual(classify_entity("whatever", {}), "entity")
        self.assertEqual(classify_entity("whatever"), "entity")

    def test_stable(self):
        self.assertEqual(classify_entity("EXP-1", {}),
                         classify_entity("EXP-1", {}))


class Warnings(unittest.TestCase):
    def test_contradiction_error_and_types(self):
        events = [
            _event(epistemic_status=EpistemicStatus.CONTRADICTION),
            _event(type="process_crashed", severity=Severity.ERROR),
            _event(type="command_rejected"),
            _event(type="process_started"),
        ]
        warnings = build_integrity_warnings(events)
        self.assertEqual(
            sorted(w["type"] for w in warnings),
            ["command_rejected", "contradiction", "error"])

    def test_clean_record_no_warnings(self):
        self.assertEqual(build_integrity_warnings([_event()]), [])


class Overview(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(build_provenance_overview([]), [])

    def test_subjects_grouped(self):
        events = [_event(), _event(subject_id="EXP-2",
                                   payload={"experiment_id": "EXP-2"})]
        overview = build_provenance_overview(events)
        self.assertEqual(len(overview), 2)
        by_id = {item["subject_id"]: item for item in overview}
        self.assertEqual(by_id["EXP-1"]["entity_type"], "evolution")
        self.assertEqual(by_id["EXP-1"]["event_count"], 1)
        self.assertEqual(by_id["EXP-1"]["warning_count"], 0)
        self.assertEqual(by_id["EXP-1"]["actors"], ["test"])

    def test_newest_first(self):
        early = _event(subject_id="OLD")
        late = _event(subject_id="NEW",
                      timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc))
        overview = build_provenance_overview([early, late])
        self.assertEqual([item["subject_id"] for item in overview],
                         ["NEW", "OLD"])


class Audit(unittest.TestCase):
    def _events(self):
        return [
            _event(payload={"experiment_id": "EXP-1",
                            "fitness_id": "FIT-1",
                            "summary": "Proposed"}),
            _event(type="experiment_authorized", subject_id="EXP-1",
                   payload={"experiment_id": "EXP-1",
                            "authorization_id": "AUTH-1"}),
            _event(category=EventCategory.EVIDENCE, type="experiment_result",
                   subject_id="EXP-1",
                   payload={"experiment_id": "EXP-1", "name": "filter",
                            "observed": "ok"},
                   evidence_refs=["EVD-1"]),
            _event(category=EventCategory.GOVERNANCE, type="command_rejected",
                   subject_id="OTHER",
                   payload={"experiment_id": "EXP-1",
                            "reason": "blocked"}),
        ]

    def test_missing_none(self):
        self.assertIsNone(build_provenance_audit("EXP-nope", self._events()))

    def test_direct_and_related(self):
        audit = build_provenance_audit("EXP-1", self._events())
        assert audit is not None
        self.assertEqual(audit["direct_event_count"], 3)
        self.assertEqual(audit["related_event_count"], 1)
        # Category precedence (governance > evidence > evolution) applies
        # as specified; the evidence-category record decides here.
        self.assertEqual(audit["entity_type"], "evidence")

    def test_hash_chain_links(self):
        audit = build_provenance_audit("EXP-1", self._events())
        assert audit is not None
        chain = audit["hash_chain"]
        self.assertEqual(len(chain), 3)
        self.assertIsNone(chain[0]["previous_event_hash"])
        for previous, current in zip(chain, chain[1:]):
            self.assertEqual(current["previous_event_hash"],
                             previous["event_hash"])
        # Chain entries recompute from stored events.
        from observatory.backend.domain import event_hash as _hash
        stored = [e for e in self._events() if e.subject_id == "EXP-1"]
        stored.sort(key=lambda e: e.timestamp)
        self.assertEqual(chain[0]["event_hash"], _hash(stored[0]))

    def test_edges_both_directions(self):
        audit = build_provenance_audit("EXP-1", self._events())
        assert audit is not None
        relations = {(e["source"], e["target"], e["relation"])
                     for e in audit["edges"]}
        self.assertIn(("EXP-1", "FIT-1", "fitness"), relations)
        self.assertIn(("OTHER", "EXP-1", "experiment"), relations)
        self.assertNotIn(("EXP-1", "EXP-1", "experiment"), relations)

    def test_nodes_warnings_governance(self):
        audit = build_provenance_audit("EXP-1", self._events())
        assert audit is not None
        node_ids = {node["id"] for node in audit["nodes"]}
        self.assertIn("EXP-1", node_ids)
        self.assertIn("FIT-1", node_ids)
        self.assertEqual(len(audit["warnings"]), 1)
        self.assertEqual(len(audit["governance_events"]), 1)
        timestamps = [t["timestamp"] for t in audit["timeline"]]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        self.assertEqual(audit["timeline"][0]["subject_id"], "OTHER")

    def test_no_secrets_in_overview(self):
        events = [_event(payload={"experiment_id": "EXP-1",
                                  "api_token": "supersecret-value"})]
        overview = build_provenance_overview(events)
        blob = str(overview)
        self.assertNotIn("supersecret-value", blob)


if __name__ == "__main__":
    unittest.main()
