"""Tiannara runtime adapter: observe-only bridge to the Observatory.

Guarantees: non-blocking observation, secret redaction before transport,
bounded retry with backoff, failure isolation with counters and an
append-only failure log. The adapter never commands, deploys, mutates,
optimizes, or executes evolution. If the Observatory is unavailable, the
runtime continues operating; backpressure drops events (counted), never
blocks.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import (HttpObservatoryTransport, ObservatoryTransport,
                     PermanentTransportError, RetryableTransportError)
from .config import TiannaraAdapterSettings
from .events import build_event, utc_now
from .redaction import redact

LOGGER = logging.getLogger("tiannara.observatory.adapter")


class TiannaraRuntimeAdapter:
    """Non-blocking observer from the Tiannara Python runtime."""

    def __init__(self, settings: TiannaraAdapterSettings,
                 transport: Optional[ObservatoryTransport] = None) -> None:
        self.settings = settings
        self.transport = transport or HttpObservatoryTransport(settings)
        self._queue: Optional[asyncio.Queue] = None
        self._worker: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stopped = False
        self.sent_events = 0
        self.dropped_events = 0
        self.failed_events = 0
        self._failure_path = (
            Path(settings.failure_log_path)
            if settings.failure_log_path else None)

    async def start(self) -> None:
        if self._worker is not None:
            return
        self._queue = asyncio.Queue(maxsize=self.settings.queue_size)
        self._stopped = False
        self._loop = asyncio.get_running_loop()
        self._worker = asyncio.create_task(
            self._run(), name="tiannara-observatory-runtime-adapter")

    async def stop(self, timeout: float = 5.0) -> None:
        if self._worker is None or self._queue is None:
            return
        self._stopped = True
        try:
            await asyncio.wait_for(self._queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            LOGGER.warning(
                "Observatory adapter stop timed out; cancelling pending events")
        self._worker.cancel()
        await asyncio.gather(self._worker, return_exceptions=True)
        await self.transport.close()
        self._worker = None
        self._loop = None

    async def observe(self, *, category: str, type: str, subject_id: str,
                      payload: Optional[Dict[str, Any]] = None,
                      severity: str = "info",
                      epistemic_status: str = "observed",
                      correlation_id: Optional[str] = None,
                      causation_id: Optional[str] = None,
                      evidence_refs: Optional[List[str]] = None,
                      provenance: Optional[Dict[str, Any]] = None) -> None:
        if self._stopped or self._queue is None:
            return
        try:
            merged_provenance = {"environment": self.settings.environment,
                                 "adapter": "tiannara-runtime-adapter"}
            if provenance:
                merged_provenance.update(provenance)
            event = build_event(
                source=self.settings.source, category=category, type=type,
                subject_id=subject_id, payload=payload, severity=severity,
                epistemic_status=epistemic_status,
                correlation_id=correlation_id, causation_id=causation_id,
                evidence_refs=evidence_refs, provenance=merged_provenance)
            if self.settings.redaction_enabled:
                event["payload"] = redact(event["payload"])
                event["provenance"] = redact(event["provenance"])
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            self.dropped_events += 1
            LOGGER.warning(
                "Observatory adapter queue full; dropping event type=%s subject=%s",
                type, subject_id)
        except ValueError:
            LOGGER.exception(
                "Failed to construct Observatory event type=%s subject=%s",
                type, subject_id)

    def observe_blocking(self, *, category: str, type: str, subject_id: str,
                         payload: Optional[Dict[str, Any]] = None,
                         severity: str = "info",
                         epistemic_status: str = "observed",
                         correlation_id: Optional[str] = None,
                         causation_id: Optional[str] = None,
                         evidence_refs: Optional[List[str]] = None,
                         provenance: Optional[Dict[str, Any]] = None) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.observe(
                    category=category, type=type, subject_id=subject_id,
                    payload=payload, severity=severity,
                    epistemic_status=epistemic_status,
                    correlation_id=correlation_id, causation_id=causation_id,
                    evidence_refs=evidence_refs, provenance=provenance),
                self._loop)
        except RuntimeError:
            return

    async def process_started(self, process_name: str,
                              supervisor: Optional[str] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        await self.observe(
            category="runtime", type="process_started",
            subject_id=process_name,
            payload={"process": process_name, "supervisor": supervisor,
                     "summary": f"{process_name} started", **(metadata or {})},
            severity="info")

    async def process_stopped(self, process_name: str,
                              reason: Optional[str] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        await self.observe(
            category="runtime", type="process_stopped",
            subject_id=process_name,
            payload={"process": process_name, "reason": reason,
                     "summary": f"{process_name} stopped", **(metadata or {})},
            severity="info")

    async def process_restarted(self, process_name: str,
                                restart_count: Optional[int] = None,
                                reason: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None) -> None:
        await self.observe(
            category="runtime", type="process_restarted",
            subject_id=process_name,
            payload={"process": process_name, "restart_count": restart_count,
                     "reason": reason,
                     "summary": f"{process_name} restarted", **(metadata or {})},
            severity="warning")

    async def process_crashed(self, process_name: str,
                              error_type: Optional[str] = None,
                              reason: Optional[str] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        await self.observe(
            category="runtime", type="process_crashed",
            subject_id=process_name,
            payload={"process": process_name, "error_type": error_type,
                     "reason": reason,
                     "summary": f"{process_name} crashed", **(metadata or {})},
            severity="error")

    async def metric(self, metric_name: str, value: Any,
                     unit: Optional[str] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        await self.observe(
            category="runtime", type="metric", subject_id=metric_name,
            payload={"metric": metric_name, "value": value, "unit": unit,
                     **(metadata or {})},
            severity="info")

    async def log_event(self, subject_id: str, message: str,
                        level: str = "info",
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        payload = {"message": message, "level": level, "summary": message,
                   **(metadata or {})}
        await self.observe(
            category="runtime", type="log", subject_id=subject_id,
            payload=payload, severity=self._severity_from_log_level(level))

    async def _run(self) -> None:
        assert self._queue is not None
        while True:
            batch: List[Dict[str, Any]] = []
            try:
                first = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=self.settings.flush_interval_seconds)
            except asyncio.TimeoutError:
                continue
            batch.append(first)
            while len(batch) < self.settings.batch_size:
                try:
                    batch.append(self._queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
            try:
                await self._send_batch(batch)
                self.sent_events += len(batch)
            except PermanentTransportError:
                await self._fallback_individual(batch)
            except Exception as exc:
                self.failed_events += len(batch)
                for event in batch:
                    self._write_failure(
                        event, f"unexpected batch error: {exc}")
            finally:
                for _ in batch:
                    self._queue.task_done()

    async def _send_batch(self, batch: List[Dict[str, Any]]) -> None:
        if not batch:
            return
        if len(batch) == 1:
            await self._send_with_retry(batch[0])
            return
        send_events = getattr(self.transport, "send_events", None)
        if send_events is None:
            for event in batch:
                await self._send_with_retry(event)
            return
        retries = 0
        delay = self.settings.initial_retry_delay_seconds
        while True:
            try:
                await send_events(batch)
                return
            except RetryableTransportError as exc:
                retries += 1
                if retries > self.settings.max_retries:
                    raise PermanentTransportError(
                        "observatory batch delivery failed after retries"
                    ) from exc
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.settings.max_retry_delay_seconds)
            except PermanentTransportError:
                raise

    async def _fallback_individual(self, batch: List[Dict[str, Any]]) -> None:
        for event in batch:
            try:
                await self._send_with_retry(event)
                self.sent_events += 1
            except PermanentTransportError as exc:
                self.failed_events += 1
                self._write_failure(event, str(exc))
            except Exception as exc:
                self.failed_events += 1
                self._write_failure(
                    event, f"unexpected individual send error: {exc}")

    async def _send_with_retry(self, event: Dict[str, Any]) -> None:
        retries = 0
        delay = self.settings.initial_retry_delay_seconds
        while True:
            try:
                await self.transport.send_event(event)
                return
            except RetryableTransportError as exc:
                retries += 1
                if retries > self.settings.max_retries:
                    raise PermanentTransportError(
                        "observatory delivery failed after retries") from exc
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.settings.max_retry_delay_seconds)
            except PermanentTransportError:
                raise

    def _write_failure(self, event: Dict[str, Any], reason: str) -> None:
        if self._failure_path is None:
            return
        try:
            self._failure_path.parent.mkdir(parents=True, exist_ok=True)
            record = {"failed_at": utc_now().isoformat(),
                      "reason": reason, "event": event}
            with self._failure_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True, default=str))
                handle.write("\n")
        except Exception:
            LOGGER.exception(
                "Failed to write Observatory adapter failure record")

    def _severity_from_log_level(self, level: str) -> str:
        normalized = str(level).strip().lower()
        if normalized in {"critical", "fatal"}:
            return "fatal"
        if normalized == "error":
            return "error"
        if normalized in {"warning", "warn"}:
            return "warning"
        if normalized == "debug":
            return "debug"
        return "info"
