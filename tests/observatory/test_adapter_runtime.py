"""Adapter transport/runtime/logging tests + backend integration.

Fake transports prove retry/backoff/drop/failure-log semantics without
network. Integration runs the adapter against the real backend TestClient
(stack: adapter → HTTP → gateway → store → projections).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import unittest

import httpx

from observatory.adapters.tiannara.client import (
    HttpObservatoryTransport, PermanentTransportError,
    RetryableTransportError)
from observatory.adapters.tiannara.logging_handler import (
    ObservatoryRuntimeLogHandler)
from observatory.adapters.tiannara.runtime_adapter import (
    TiannaraRuntimeAdapter)
from tests.observatory.test_adapter import _settings


class FakeTransport:
    def __init__(self, script):
        self._script = list(script)
        self.sent = []
        self.closed = False

    async def send_event(self, event):
        self.sent.append(event)
        behavior = self._script.pop(0) if self._script else "ok"
        if behavior == "ok":
            return
        if behavior == "retryable":
            raise RetryableTransportError("boom")
        raise PermanentTransportError("nope")

    async def close(self):
        self.closed = True


class Client(unittest.TestCase):
    def _transport(self, handler):
        settings = _settings()
        transport = HttpObservatoryTransport.__new__(HttpObservatoryTransport)
        transport._settings = settings
        transport._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://test")
        return transport

    def test_success_statuses(self):
        async def scenario():
            for status in (200, 201, 202):
                transport = self._transport(
                    lambda request: httpx.Response(status))
                await transport.send_event({"id": "x"})
                await transport.close()

        asyncio.run(scenario())

    def test_retryable_on_500_and_timeout(self):
        async def scenario():
            transport = self._transport(
                lambda request: httpx.Response(500))
            with self.assertRaises(RetryableTransportError):
                await transport.send_event({"id": "x"})
            await transport.close()

            def timeout(request):
                raise httpx.TimeoutException("slow")

            transport = self._transport(timeout)
            with self.assertRaises(RetryableTransportError):
                await transport.send_event({"id": "x"})
            await transport.close()

        asyncio.run(scenario())

    def test_permanent_on_409_and_400(self):
        async def scenario():
            for status in (409, 400, 403):
                transport = self._transport(
                    lambda request, status=status: httpx.Response(status))
                with self.assertRaises(PermanentTransportError):
                    await transport.send_event({"id": "x"})
                await transport.close()

        asyncio.run(scenario())


class RuntimeAdapter(unittest.TestCase):
    def test_observe_delivers(self):
        async def scenario():
            transport = FakeTransport([])
            adapter = TiannaraRuntimeAdapter(_settings(), transport=transport)
            await adapter.start()
            await adapter.process_started("AgencyLoop", supervisor="Runtime")
            await adapter.stop()
            return adapter, transport

        adapter, transport = asyncio.run(scenario())
        self.assertEqual(adapter.sent_events, 1)
        self.assertEqual(transport.sent[0]["type"], "process_started")
        self.assertTrue(transport.closed)

    def test_retry_then_success(self):
        async def scenario():
            transport = FakeTransport(["retryable", "retryable", "ok"])
            adapter = TiannaraRuntimeAdapter(
                _settings(max_retries=3), transport=transport)
            await adapter.start()
            await adapter.metric("m", 1.0)
            await adapter.stop()
            return adapter, transport

        adapter, transport = asyncio.run(scenario())
        self.assertEqual(adapter.sent_events, 1)
        self.assertEqual(len(transport.sent), 3)

    def test_retry_exhaustion_logs_failure(self):
        tmp = tempfile.TemporaryDirectory()
        failure_log = os.path.join(tmp.name, "failures.jsonl")

        async def scenario():
            transport = FakeTransport(["retryable"] * 10)
            adapter = TiannaraRuntimeAdapter(
                _settings(failure_log_path=failure_log),
                transport=transport)
            await adapter.start()
            await adapter.metric("m", 1.0)
            await adapter.stop()
            return adapter

        adapter = asyncio.run(scenario())
        self.assertEqual(adapter.sent_events, 0)
        self.assertEqual(adapter.failed_events, 1)
        with open(failure_log, encoding="utf-8") as handle:
            record = json.loads(handle.read())
        self.assertIn("retries", record["reason"])
        tmp.cleanup()

    def test_queue_full_drops_and_counts(self):
        async def scenario():
            transport = FakeTransport([])
            adapter = TiannaraRuntimeAdapter(
                _settings(queue_size=1), transport=transport)
            await adapter.start()
            for index in range(5):
                await adapter.observe(
                    category="runtime", type="log", subject_id=f"S-{index}",
                    payload={"message": f"m{index}"})
            dropped_at_enqueue = adapter.dropped_events
            await adapter.stop()
            return dropped_at_enqueue, adapter

        dropped, adapter = asyncio.run(scenario())
        self.assertGreaterEqual(dropped, 0)
        self.assertEqual(
            adapter.sent_events + adapter.failed_events + dropped, 5)

    def test_observe_after_stop_is_silent(self):
        async def scenario():
            transport = FakeTransport([])
            adapter = TiannaraRuntimeAdapter(_settings(), transport=transport)
            await adapter.start()
            await adapter.stop()
            await adapter.observe(category="runtime", type="log",
                                  subject_id="S", payload={"message": "m"})
            return adapter

        adapter = asyncio.run(scenario())
        self.assertEqual(adapter.sent_events, 0)

    def test_redaction_before_transport(self):
        async def scenario():
            transport = FakeTransport([])
            adapter = TiannaraRuntimeAdapter(_settings(), transport=transport)
            await adapter.start()
            await adapter.observe(
                category="runtime", type="log", subject_id="S",
                payload={"api_token": "supersecret-value", "ok": True})
            await adapter.stop()
            return transport

        transport = asyncio.run(scenario())
        self.assertEqual(transport.sent[0]["payload"]["api_token"],
                         "[REDACTED]")
        self.assertTrue(transport.sent[0]["payload"]["ok"])

    def test_helpers_emit_typed_events(self):
        async def scenario():
            transport = FakeTransport([])
            adapter = TiannaraRuntimeAdapter(_settings(), transport=transport)
            await adapter.start()
            await adapter.process_stopped("P", reason="done")
            await adapter.process_restarted("P", restart_count=2)
            await adapter.process_crashed("P", error_type="RuntimeError")
            await adapter.log_event("S", "hello", level="error")
            await adapter.stop()
            return transport

        transport = asyncio.run(scenario())
        by_type = {event["type"]: event for event in transport.sent}
        self.assertEqual(by_type["process_crashed"]["severity"], "error")
        self.assertEqual(by_type["process_restarted"]["severity"], "warning")
        self.assertEqual(by_type["log"]["payload"]["level"], "error")


class LoggingHandler(unittest.TestCase):
    def test_emit_forwards(self):
        records = []

        class SinkTransport(FakeTransport):
            pass

        async def scenario():
            transport = FakeTransport([])
            adapter = TiannaraRuntimeAdapter(_settings(), transport=transport)
            await adapter.start()
            logger = logging.getLogger("test.observatory.handler")
            logger.handlers.clear()
            logger.setLevel(logging.DEBUG)
            logger.addHandler(ObservatoryRuntimeLogHandler(adapter))
            try:
                logger.error("kaboom", exc_info=RuntimeError("bad"))
                # observe_blocking is fire-and-forget by design; poll for
                # delivery instead of assuming synchronous arrival.
                for _ in range(100):
                    if transport.sent:
                        break
                    await asyncio.sleep(0.05)
            finally:
                logger.handlers.clear()
            await adapter.stop()
            records.extend(transport.sent)

        asyncio.run(scenario())
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["payload"]["error_type"], "RuntimeError")

    def test_emit_never_raises(self):
        class BrokenAdapter:
            def observe_blocking(self, **kwargs):
                raise RuntimeError("dead")

        logger = logging.getLogger("test.observatory.broken")
        logger.handlers.clear()
        logger.addHandler(ObservatoryRuntimeLogHandler(BrokenAdapter()))  # type: ignore[arg-type]
        try:
            logger.error("still fine")
        finally:
            logger.handlers.clear()


class Integration(unittest.TestCase):
    def test_adapter_to_backend_end_to_end(self):
        import observatory.backend.main as main_module
        from fastapi.testclient import TestClient
        from observatory.backend.main import create_app

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        os.environ["OBSERVATORY_DB_PATH"] = os.path.join(tmp.name, "obs.sqlite3")
        os.environ["OBSERVATORY_API_TOKEN"] = "test-token"
        main_module.get_settings.cache_clear()
        client = TestClient(create_app())
        from tests.observatory.conftest import register_store_cleanup
        register_store_cleanup(self, client)

        received = {}

        class DirectTransport:
            async def send_event(self, event):
                response = client.post(
                    "/observatory/events", json=event,
                    headers={"X-Actor-Id": "adapter", "X-Actor-Role": "system",
                             "X-Observatory-Token": "test-token"})
                received["status"] = response.status_code
                if response.status_code not in {200, 201, 202}:
                    from observatory.adapters.tiannara.client import (
                        PermanentTransportError as Permanent)
                    raise Permanent(f"status {response.status_code}")

            async def close(self):
                pass

        async def scenario():
            adapter = TiannaraRuntimeAdapter(
                _settings(), transport=DirectTransport())
            await adapter.start()
            await adapter.process_started("AgencyLoop", supervisor="Runtime")
            await adapter.metric("messages_per_sec", 4.8, unit="msg/s")
            await adapter.stop()
            return adapter

        adapter = asyncio.run(scenario())
        self.assertEqual(adapter.sent_events, 2)
        self.assertEqual(received["status"], 200)
        trace = client.get("/observatory/trace/AgencyLoop")
        self.assertEqual(trace.status_code, 200)
        self.assertEqual(len(trace.json()), 1)
        metrics = client.get("/observatory/trace/messages_per_sec")
        self.assertEqual(metrics.status_code, 200)


if __name__ == "__main__":
    unittest.main()
