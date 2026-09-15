"""Adapter unit tests: config, redaction, event construction."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from observatory.adapters.tiannara import redaction
from observatory.adapters.tiannara.config import TiannaraAdapterSettings
from observatory.adapters.tiannara.events import (
    build_event, generate_event_id)


def _settings(**overrides) -> TiannaraAdapterSettings:
    base = {"observatory_base_url": "http://127.0.0.1:8000", "api_token": None,
            "source": "test", "environment": "test", "actor_id": "a",
            "actor_role": "system", "timeout_seconds": 1.0, "queue_size": 100,
            "max_retries": 1, "initial_retry_delay_seconds": 0.01,
            "max_retry_delay_seconds": 0.05, "redaction_enabled": True,
            "failure_log_path": None, "batch_size": 10,
            "flush_interval_seconds": 0.05}
    base.update(overrides)
    return TiannaraAdapterSettings(**base)


class Config(unittest.TestCase):
    def test_frozen(self):
        settings = _settings()
        with self.assertRaises(Exception):
            settings.source = "mutated"  # type: ignore[misc]

    def test_env_parsing(self):
        import os
        from observatory.adapters.tiannara.config import (
            get_adapter_settings)
        os.environ["OBSERVATORY_ADAPTER_QUEUE_SIZE"] = "not-a-number"
        os.environ["OBSERVATORY_ADAPTER_REDACTION_ENABLED"] = "off"
        try:
            get_adapter_settings.cache_clear()
            settings = get_adapter_settings()
            self.assertEqual(settings.queue_size, 10_000)
            self.assertIs(settings.redaction_enabled, False)
        finally:
            del os.environ["OBSERVATORY_ADAPTER_QUEUE_SIZE"]
            del os.environ["OBSERVATORY_ADAPTER_REDACTION_ENABLED"]
            get_adapter_settings.cache_clear()


class Redaction(unittest.TestCase):
    def test_secret_keys(self):
        cleaned = redaction.redact(
            {"password": "hunter2-hunter2", "name": "x",
             "nested": {"api_token": "toktoktoktoktoktok"}})
        self.assertEqual(cleaned["password"], "[REDACTED]")
        self.assertEqual(cleaned["nested"]["api_token"], "[REDACTED]")
        self.assertEqual(cleaned["name"], "x")

    def test_case_insensitive(self):
        self.assertEqual(
            redaction.redact({"Authorization": "Bearer abc"})["Authorization"],
            "[REDACTED]")

    def test_truncation_marked(self):
        long_string = "x" * 5000
        cleaned = redaction.redact({"note": long_string})
        self.assertTrue(cleaned["note"].endswith("...[truncated]"))

    def test_depth_bounded(self):
        deep: object = {"level": None}
        current = deep
        assert isinstance(current, dict)
        for _ in range(15):
            child: dict = {"level": None}
            current["level"] = child
            current = child
        cleaned = redaction.redact(deep)
        self.assertIn("[MAX_DEPTH]", str(cleaned))

    def test_tuple_normalized(self):
        self.assertEqual(redaction.redact({"items": ("a", "b")})["items"],
                         ["a", "b"])

    def test_non_string_passthrough(self):
        self.assertEqual(redaction.redact({"count": 3})["count"], 3)


class Events(unittest.TestCase):
    def test_validation(self):
        with self.assertRaises(ValueError):
            build_event(source="s", category="nope", type="t",
                        subject_id="x")
        with self.assertRaises(ValueError):
            build_event(source="s", category="runtime", type="t",
                        subject_id="x", severity="extreme")
        with self.assertRaises(ValueError):
            build_event(source="", category="runtime", type="t",
                        subject_id="x")

    def test_deterministic_id(self):
        timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
        kwargs = {"source": "s", "category": "runtime", "type": "t",
                  "subject_id": "x", "payload": {"a": 1},
                  "timestamp": timestamp}
        self.assertEqual(generate_event_id(**kwargs),
                         generate_event_id(**kwargs))

    def test_build_shape(self):
        event = build_event(source="s", category="evidence", type="t",
                            subject_id="E-1")
        self.assertTrue(event["id"].startswith("evt-evidence-"))
        self.assertEqual(event["epistemic_status"], "observed")
        self.assertEqual(event["severity"], "info")
        self.assertEqual(event["evidence_refs"], [])


if __name__ == "__main__":
    unittest.main()
