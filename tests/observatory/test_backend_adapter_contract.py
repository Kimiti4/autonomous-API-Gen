"""Backend <-> adapter vocabulary contract tests (D36 T1, DEC-001).

The backend domain vocabulary (observatory.backend.domain) is the contract of
record; the adapter mirror (observatory.adapters.tiannara.events) conforms.
These tests bind the two WITHOUT merging them: the adapter must remain
importable without the backend package (deployment decoupling is preserved).

Every assertion here is DERIVED from current code on both sides. If a test
fails after a change to either side, the change introduced vocabulary drift
(DUP-001/GAP-005) and must be reconciled explicitly — never by weakening the
test to match the drift.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from pydantic import ValidationError

from observatory.adapters.tiannara import events as adapter_events
from observatory.adapters.tiannara.redaction import (
    SECRET_KEY_MARKERS as ADAPTER_MARKERS,
    is_secret_key as adapter_is_secret_key,
)
from observatory.backend.domain import (
    EpistemicStatus,
    EventCategory,
    Severity,
    generate_event_id as backend_generate_event_id,
    new_event,
    parse_timestamp as backend_parse_timestamp,
)
from observatory.backend.gateway import (
    SECRET_KEY_MARKERS as BACKEND_MARKERS,
)

FIXED_AT = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


class VocabularyParity(unittest.TestCase):
    def test_category_sets_match(self):
        backend = {item.value for item in EventCategory}
        self.assertEqual(set(adapter_events.VALID_CATEGORIES), backend)

    def test_severity_sets_match(self):
        backend = {item.value for item in Severity}
        self.assertEqual(set(adapter_events.VALID_SEVERITIES), backend)

    def test_epistemic_sets_match(self):
        backend = {item.value for item in EpistemicStatus}
        self.assertEqual(set(adapter_events.VALID_EPISTEMIC_STATUSES),
                         backend)

    def test_invalid_category_rejected_both(self):
        with self.assertRaises(ValueError):
            adapter_events.build_event(
                source="s", category="nope", type="t", subject_id="S")
        # Observed error-type asymmetry (CURRENT_FACT, not a contract ideal):
        # the backend touches category.value during id generation before
        # Pydantic validation, so an invalid category escapes as
        # AttributeError while the adapter raises ValueError. Both sides
        # REJECT; neither accepts. If either side changes its error type,
        # this test must be reconciled explicitly, never silenced.
        with self.assertRaises(AttributeError):
            new_event(category="nope", source="s", type="t",  # type: ignore
                      subject_id="S")

    def test_invalid_severity_rejected_both(self):
        with self.assertRaises(ValueError):
            adapter_events.build_event(
                source="s", category="runtime", type="t", subject_id="S",
                severity="nope")
        with self.assertRaises((ValueError, ValidationError)):
            new_event(category=EventCategory.RUNTIME, source="s", type="t",
                      subject_id="S", severity="nope")  # type: ignore

    def test_invalid_epistemic_rejected_both(self):
        with self.assertRaises(ValueError):
            adapter_events.build_event(
                source="s", category="runtime", type="t", subject_id="S",
                epistemic_status="nope")
        with self.assertRaises((ValueError, ValidationError)):
            new_event(category=EventCategory.RUNTIME, source="s", type="t",
                      subject_id="S",
                      epistemic_status="nope")  # type: ignore

    def test_required_fields_rejected_both(self):
        for kwargs in ({"source": ""}, {"type": ""}, {"subject_id": ""}):
            base = {"source": "s", "category": "runtime", "type": "t",
                    "subject_id": "S"}
            base.update(kwargs)
            with self.assertRaises(ValueError, msg=str(kwargs)):
                adapter_events.build_event(**base)
            with self.assertRaises(ValueError, msg=str(kwargs)):
                new_event(category=EventCategory.RUNTIME, **{
                    k: v for k, v in base.items() if k != "category"})


class IdentityParity(unittest.TestCase):
    def test_same_inputs_same_id(self):
        payload = {"task": "INC-01", "n": 7}
        backend_id = backend_generate_event_id(
            category=EventCategory.RUNTIME, source="probe", type="tick",
            subject_id="SUBJ-9", payload=payload, timestamp=FIXED_AT)
        adapter_id = adapter_events.generate_event_id(
            source="probe", category="runtime", type="tick",
            subject_id="SUBJ-9", payload=payload, timestamp=FIXED_AT)
        self.assertEqual(backend_id, adapter_id)
        self.assertTrue(backend_id.startswith("evt-runtime-"))

    def test_explicit_id_preserved_both(self):
        backend_event = new_event(
            category=EventCategory.EVIDENCE, source="s", type="t",
            subject_id="S", id="evt-custom-1")
        adapter_event = adapter_events.build_event(
            source="s", category="evidence", type="t", subject_id="S",
            event_id="evt-custom-1")
        self.assertEqual(backend_event.id, "evt-custom-1")
        self.assertEqual(adapter_event["id"], "evt-custom-1")


class TimestampParity(unittest.TestCase):
    def test_none_is_tz_aware_now_both(self):
        for parsed in (backend_parse_timestamp(None),
                       adapter_events.parse_timestamp(None)):
            self.assertIsNotNone(parsed.tzinfo)
            self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_naive_coerced_utc_both(self):
        naive = datetime(2026, 3, 1, 8, 30, 0)
        for parsed in (backend_parse_timestamp(naive),
                       adapter_events.parse_timestamp(naive)):
            self.assertEqual(parsed.tzinfo, timezone.utc)
            self.assertEqual((parsed.year, parsed.month, parsed.day),
                             (2026, 3, 1))

    def test_invalid_raises_both(self):
        with self.assertRaises(ValueError):
            backend_parse_timestamp("not-a-timestamp")
        with self.assertRaises(ValueError):
            adapter_events.parse_timestamp("not-a-timestamp")

    def test_zulu_accepted_both(self):
        for parsed in (backend_parse_timestamp("2026-01-01T00:00:00Z"),
                       adapter_events.parse_timestamp(
                           "2026-01-01T00:00:00Z")):
            self.assertEqual(parsed.tzinfo, timezone.utc)


class RedactionMarkerContract(unittest.TestCase):
    def test_adapter_markers_superset_documented(self):
        # DUP-002, pinned: the adapter set MUST remain a superset of the
        # backend set, and the delta MUST remain exactly {"authorization"}.
        # Any other divergence is vocabulary drift, not a passing test.
        self.assertTrue(set(BACKEND_MARKERS) <= set(ADAPTER_MARKERS))
        self.assertEqual(set(ADAPTER_MARKERS) - set(BACKEND_MARKERS),
                         {"authorization"})

    def test_predicates_agree_on_backend_markers(self):
        from observatory.backend.gateway import ObservatoryGateway

        gateway = ObservatoryGateway.__new__(ObservatoryGateway)
        for marker in BACKEND_MARKERS:
            key = f"operator_{marker}_ref"
            with self.subTest(marker=marker):
                self.assertTrue(gateway._secret_key(key))
                self.assertTrue(adapter_is_secret_key(key))

    def test_benign_keys_agree_negative(self):
        from observatory.backend.gateway import ObservatoryGateway

        gateway = ObservatoryGateway.__new__(ObservatoryGateway)
        for key in ("subject_id", "event_type", "summary", "owner_id"):
            with self.subTest(key=key):
                self.assertFalse(gateway._secret_key(key))
                self.assertFalse(adapter_is_secret_key(key))


class DefaultParity(unittest.TestCase):
    def test_epistemic_default_observed_both(self):
        backend_event = new_event(
            category=EventCategory.RUNTIME, source="s", type="t",
            subject_id="S")
        adapter_event = adapter_events.build_event(
            source="s", category="runtime", type="t", subject_id="S")
        self.assertEqual(backend_event.epistemic_status,
                         EpistemicStatus.OBSERVED)
        self.assertEqual(adapter_event["epistemic_status"], "observed")

    def test_severity_default_info_both(self):
        backend_event = new_event(
            category=EventCategory.RUNTIME, source="s", type="t",
            subject_id="S")
        adapter_event = adapter_events.build_event(
            source="s", category="runtime", type="t", subject_id="S")
        self.assertEqual(backend_event.severity, Severity.INFO)
        self.assertEqual(adapter_event["severity"], "info")


if __name__ == "__main__":
    unittest.main()
