"""Adapter batch behavior tests (explicit asyncio markers; strict mode).

NOTE (repo adaptation): no root pytest.ini is created (it would override
pyproject.toml's canonical test configuration). Async tests use explicit
@pytest.mark.asyncio markers instead of asyncio_mode=auto.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import pytest

from observatory.adapters.tiannara.client import PermanentTransportError

from observatory.adapters.tiannara.client import PermanentTransportError
from observatory.adapters.tiannara.config import TiannaraAdapterSettings
from observatory.adapters.tiannara.runtime_adapter import TiannaraRuntimeAdapter


def make_settings(batch_size: int = 2,
                  flush_interval_seconds: float = 0.01
                  ) -> TiannaraAdapterSettings:
    return TiannaraAdapterSettings(
        observatory_base_url="http://observatory.test",
        api_token=None, source="tiannara.test", environment="test",
        actor_id="tiannara-test-adapter", actor_role="system",
        timeout_seconds=1.0, queue_size=100, max_retries=2,
        initial_retry_delay_seconds=0.01, max_retry_delay_seconds=0.02,
        redaction_enabled=True, failure_log_path=None,
        batch_size=batch_size, flush_interval_seconds=flush_interval_seconds)


class FakeTransport:
    def __init__(self, fail_batch: bool = False) -> None:
        self.fail_batch = fail_batch
        self.sent_events: List[Dict[str, Any]] = []
        self.sent_batches: List[List[Dict[str, Any]]] = []

    async def send_event(self, event: Dict[str, Any]) -> None:
        self.sent_events.append(event)

    async def send_events(self, events: List[Dict[str, Any]]) -> None:
        if self.fail_batch:
            raise PermanentTransportError("batch rejected")
        self.sent_batches.append(list(events))

    async def close(self) -> None:
        return None


async def wait_for_condition(condition, timeout: float = 2.0) -> None:
    async def poll() -> None:
        while not condition():
            await asyncio.sleep(0.01)

    await asyncio.wait_for(poll(), timeout=timeout)


@pytest.mark.asyncio
async def test_adapter_sends_batch_when_batch_size_reached():
    settings = make_settings(batch_size=2)
    transport = FakeTransport()
    adapter = TiannaraRuntimeAdapter(settings, transport=transport)
    await adapter.start()
    await adapter.observe(category="runtime", type="test_event",
                          subject_id="SUBJECT-1", payload={"index": 1})
    await adapter.observe(category="runtime", type="test_event",
                          subject_id="SUBJECT-2", payload={"index": 2})
    await wait_for_condition(lambda: adapter.sent_events == 2)
    await adapter.stop()
    assert len(transport.sent_batches) == 1
    assert len(transport.sent_batches[0]) == 2
    assert adapter.sent_events == 2
    assert adapter.failed_events == 0


@pytest.mark.asyncio
async def test_adapter_falls_back_to_individual_send_when_batch_rejected():
    # Routing is timing-dependent (worker may drain singletons), so assert
    # the routing rule directly plus end-state delivery through the worker.
    from observatory.adapters.tiannara.runtime_adapter import (
        TiannaraRuntimeAdapter as Adapter)
    settings = make_settings(batch_size=2)
    routing = FakeTransport(fail_batch=True)
    adapter = Adapter(settings, transport=routing)
    # A rejected multi-batch surfaces Permanent (the worker converts this
    # into individual fallback); nothing is delivered by the batch path.
    with pytest.raises(PermanentTransportError):
        await adapter._send_batch([{"id": "r-1"}, {"id": "r-2"}])
    assert routing.sent_batches == []
    assert routing.sent_events == []
    await adapter._fallback_individual([{"id": "r-1"}, {"id": "r-2"}])
    assert [e["id"] for e in routing.sent_events] == ["r-1", "r-2"]
    assert adapter.sent_events == 2

    transport = FakeTransport(fail_batch=True)
    adapter = TiannaraRuntimeAdapter(settings, transport=transport)
    await adapter.start()
    await adapter.observe(category="runtime", type="test_event",
                          subject_id="SUBJECT-1", payload={"index": 1})
    await adapter.observe(category="runtime", type="test_event",
                          subject_id="SUBJECT-2", payload={"index": 2})
    await wait_for_condition(lambda: adapter.sent_events == 2)
    await adapter.stop()
    assert adapter.sent_events == 2
    assert adapter.failed_events == 0


@pytest.mark.asyncio
async def test_adapter_redacts_secret_payload_fields():
    settings = make_settings(batch_size=1)
    transport = FakeTransport()
    adapter = TiannaraRuntimeAdapter(settings, transport=transport)
    await adapter.start()
    await adapter.observe(
        category="runtime", type="test_event", subject_id="SUBJECT-SECRET",
        payload={"password": "super-secret-value",
                 "summary": "event containing secret"})
    await wait_for_condition(lambda: adapter.sent_events == 1)
    await adapter.stop()
    assert len(transport.sent_events) == 1
    event = transport.sent_events[0]
    assert event["payload"]["password"] == "[REDACTED]"
    assert event["payload"]["summary"] == "event containing secret"
