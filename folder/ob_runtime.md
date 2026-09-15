Yes — the next required backend component is the **Tiannara runtime adapter**.

This adapter connects the real Python Tiannara runtime to the Observatory backend. It observes runtime occurrences and converts them into canonical Observatory events. It does **not** mutate Tiannara, does **not** issue commands, and does **not** become a blocking dependency for the runtime.

Architecturally:

```text
Tiannara runtime
      ↓
TiannaraRuntimeAdapter
      ↓
Observatory HTTP API
      ↓
Observatory event store
      ↓
Projections / UI / traceability
```

The adapter is an **observer**, not an executive.

---

# 1. Production correction to the existing backend

Before adding the adapter, one dependency-injection correction is required in the backend.

In the previous `observatory/backend/api/deps.py`, the writer/operator dependencies should explicitly depend on `get_actor`.

Replace the previous `require_writer` and `require_operator` with this corrected version.

**`observatory/backend/api/deps.py`**

```python
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request

from ..config import get_settings
from ..domain import Actor


def get_gateway(request: Request):
    return request.app.state.gateway


def get_actor(
    x_actor_id: Optional[str] = Header(default=None),
    x_actor_role: Optional[str] = Header(default=None),
    x_actor_clearance: Optional[str] = Header(default=None),
) -> Actor:
    return Actor(
        id=x_actor_id or "anonymous",
        role=x_actor_role or "observer",
        clearance=x_actor_clearance or x_actor_role or "observer",
    )


def require_writer(
    actor: Actor = Depends(get_actor),
    x_observatory_token: Optional[str] = Header(default=None),
) -> Actor:
    settings = get_settings()

    if settings.api_token and x_observatory_token != settings.api_token:
        raise HTTPException(status_code=401, detail="invalid observatory token")

    if actor.role not in {"operator", "architect", "admin", "system"}:
        raise HTTPException(status_code=403, detail="writer role required")

    return actor


def require_operator(
    actor: Actor = Depends(get_actor),
    x_observatory_token: Optional[str] = Header(default=None),
) -> Actor:
    settings = get_settings()

    if settings.api_token and x_observatory_token != settings.api_token:
        raise HTTPException(status_code=401, detail="invalid observatory token")

    clearance = actor.clearance or actor.role

    if clearance not in {"operator", "architect", "admin"}:
        raise HTTPException(status_code=403, detail="operator clearance required")

    return actor
```

---

# 2. Adapter location

Add this package:

```text
observatory/
└── adapters/
    ├── __init__.py
    └── tiannara/
        ├── __init__.py
        ├── config.py
        ├── redaction.py
        ├── events.py
        ├── client.py
        ├── runtime_adapter.py
        └── logging_handler.py
```

Add dependency:

```text
httpx>=0.27.0
```

---

# 3. Adapter configuration

**`observatory/adapters/tiannara/config.py`**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)

    if raw is None:
        return default

    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)

    if raw is None:
        return default

    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class TiannaraAdapterSettings:
    observatory_base_url: str
    api_token: Optional[str]
    source: str
    environment: str
    actor_id: str
    actor_role: str
    timeout_seconds: float
    queue_size: int
    max_retries: int
    initial_retry_delay_seconds: float
    max_retry_delay_seconds: float
    redaction_enabled: bool
    failure_log_path: Optional[str]


@lru_cache
def get_adapter_settings() -> TiannaraAdapterSettings:
    return TiannaraAdapterSettings(
        observatory_base_url=os.getenv(
            "OBSERVATORY_BASE_URL",
            "http://127.0.0.1:8000",
        ),
        api_token=os.getenv("OBSERVATORY_API_TOKEN") or None,
        source=os.getenv("OBSERVATORY_ADAPTER_SOURCE", "tiannara.runtime"),
        environment=os.getenv("OBSERVATORY_ADAPTER_ENVIRONMENT", "local"),
        actor_id=os.getenv("OBSERVATORY_ADAPTER_ACTOR_ID", "tiannara-runtime-adapter"),
        actor_role=os.getenv("OBSERVATORY_ADAPTER_ACTOR_ROLE", "system"),
        timeout_seconds=_env_float("OBSERVATORY_ADAPTER_TIMEOUT_SECONDS", 2.0),
        queue_size=_env_int("OBSERVATORY_ADAPTER_QUEUE_SIZE", 10_000),
        max_retries=_env_int("OBSERVATORY_ADAPTER_MAX_RETRIES", 3),
        initial_retry_delay_seconds=_env_float(
            "OBSERVATORY_ADAPTER_INITIAL_RETRY_DELAY_SECONDS",
            0.1,
        ),
        max_retry_delay_seconds=_env_float(
            "OBSERVATORY_ADAPTER_MAX_RETRY_DELAY_SECONDS",
            2.0,
        ),
        redaction_enabled=_env_bool("OBSERVATORY_ADAPTER_REDACTION_ENABLED", True),
        failure_log_path=os.getenv(
            "OBSERVATORY_ADAPTER_FAILURE_LOG_PATH",
            "observatory_adapter_failures.jsonl",
        ),
    )
```

---

# 4. Redaction

**`observatory/adapters/tiannara/redaction.py`**

```python
from __future__ import annotations

from typing import Any

SECRET_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "credential",
    "api_key",
    "apikey",
    "private_key",
    "session",
    "authorization",
)

MAX_STRING_LENGTH = 4000
MAX_DEPTH = 10


def is_secret_key(key: Any) -> bool:
    normalized = str(key).lower()
    return any(marker in normalized for marker in SECRET_KEY_MARKERS)


def truncate_string(value: str) -> str:
    if len(value) <= MAX_STRING_LENGTH:
        return value

    return value[:MAX_STRING_LENGTH] + "...[truncated]"


def redact(value: Any, depth: int = MAX_DEPTH) -> Any:
    if depth < 0:
        return "[MAX_DEPTH]"

    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if is_secret_key(key) else redact(item, depth - 1)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [redact(item, depth - 1) for item in value]

    if isinstance(value, tuple):
        return [redact(item, depth - 1) for item in value]

    if isinstance(value, str):
        return truncate_string(value)

    return value
```

---

# 5. Canonical event construction

**`observatory/adapters/tiannara/events.py`**

```python
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

VALID_CATEGORIES = {
    "runtime",
    "evidence",
    "evolution",
    "governance",
    "knowledge",
}

VALID_SEVERITIES = {
    "debug",
    "info",
    "warning",
    "error",
    "fatal",
}

VALID_EPISTEMIC_STATUSES = {
    "observed",
    "inferred",
    "unknown",
    "contradiction",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_timestamp(value: Any) -> datetime:
    if value is None:
        return utc_now()

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    parsed = datetime.fromisoformat(str(value))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def generate_event_id(
    *,
    source: str,
    category: str,
    type: str,
    subject_id: str,
    payload: Dict[str, Any],
    timestamp: datetime,
) -> str:
    basis = canonical_json(
        {
            "source": source,
            "category": category,
            "type": type,
            "subject_id": subject_id,
            "payload": payload,
            "timestamp": timestamp.isoformat(),
        }
    )

    digest = sha256_hex(basis)
    return f"evt-{category}-{digest[:24]}"


def build_event(
    *,
    source: str,
    category: str,
    type: str,
    subject_id: str,
    payload: Optional[Dict[str, Any]] = None,
    severity: str = "info",
    epistemic_status: str = "observed",
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    evidence_refs: Optional[List[str]] = None,
    provenance: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    if category not in VALID_CATEGORIES:
        raise ValueError(f"invalid event category: {category}")

    if severity not in VALID_SEVERITIES:
        raise ValueError(f"invalid event severity: {severity}")

    if epistemic_status not in VALID_EPISTEMIC_STATUSES:
        raise ValueError(f"invalid epistemic status: {epistemic_status}")

    if not source:
        raise ValueError("event source is required")

    if not type:
        raise ValueError("event type is required")

    if not subject_id:
        raise ValueError("event subject_id is required")

    resolved_timestamp = parse_timestamp(timestamp)
    resolved_payload = dict(payload or {})

    resolved_id = event_id or generate_event_id(
        source=source,
        category=category,
        type=type,
        subject_id=subject_id,
        payload=resolved_payload,
        timestamp=resolved_timestamp,
    )

    return {
        "id": resolved_id,
        "timestamp": resolved_timestamp.isoformat(),
        "source": source,
        "category": category,
        "type": type,
        "subject_id": subject_id,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "payload": resolved_payload,
        "epistemic_status": epistemic_status,
        "authorization": None,
        "evidence_refs": list(evidence_refs or []),
        "provenance": dict(provenance or {}),
        "severity": severity,
    }
```

---

# 6. Observatory transport client

**`observatory/adapters/tiannara/client.py`**

```python
from __future__ import annotations

from typing import Any, Dict, Protocol

import httpx

from .config import TiannaraAdapterSettings


class RetryableTransportError(Exception):
    pass


class PermanentTransportError(Exception):
    pass


class ObservatoryTransport(Protocol):
    async def send_event(self, event: Dict[str, Any]) -> None:
        ...

    async def close(self) -> None:
        ...


class HttpObservatoryTransport:
    def __init__(self, settings: TiannaraAdapterSettings) -> None:
        self._settings = settings

        headers = {
            "Content-Type": "application/json",
            "X-Actor-Id": settings.actor_id,
            "X-Actor-Role": settings.actor_role,
            "X-Actor-Clearance": "system",
        }

        if settings.api_token:
            headers["X-Observatory-Token"] = settings.api_token

        self._client = httpx.AsyncClient(
            base_url=settings.observatory_base_url,
            timeout=settings.timeout_seconds,
            headers=headers,
        )

    async def send_event(self, event: Dict[str, Any]) -> None:
        try:
            response = await self._client.post(
                "/observatory/events",
                json=event,
            )
        except httpx.TimeoutException as exc:
            raise RetryableTransportError("observatory request timed out") from exc
        except httpx.TransportError as exc:
            raise RetryableTransportError("observatory transport error") from exc

        if response.status_code in {200, 201, 202}:
            return

        if response.status_code == 409:
            raise PermanentTransportError(
                f"observatory event integrity conflict: {response.text[:200]}"
            )

        if 400 <= response.status_code < 500:
            raise PermanentTransportError(
                f"observatory rejected event: {response.status_code} {response.text[:200]}"
            )

        raise RetryableTransportError(
            f"observatory returned retryable status: {response.status_code}"
        )

    async def close(self) -> None:
        await self._client.aclose()
```

---

# 7. Tiannara runtime adapter

**`observatory/adapters/tiannara/runtime_adapter.py`**

```python
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import (
    HttpObservatoryTransport,
    ObservatoryTransport,
    PermanentTransportError,
    RetryableTransportError,
)
from .config import TiannaraAdapterSettings
from .events import build_event, utc_now
from .redaction import redact

LOGGER = logging.getLogger("tiannara.observatory.adapter")


class TiannaraRuntimeAdapter:
    """
    Non-blocking adapter from the Tiannara Python runtime to the Observatory.

    This adapter only observes. It does not command, deploy, mutate,
    optimize, or execute evolution.
    """

    def __init__(
        self,
        settings: TiannaraAdapterSettings,
        transport: Optional[ObservatoryTransport] = None,
    ) -> None:
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
            if settings.failure_log_path
            else None
        )

    async def start(self) -> None:
        if self._worker is not None:
            return

        self._queue = asyncio.Queue(maxsize=self.settings.queue_size)
        self._stopped = False
        self._loop = asyncio.get_running_loop()
        self._worker = asyncio.create_task(
            self._run(),
            name="tiannara-observatory-runtime-adapter",
        )

    async def stop(self, timeout: float = 5.0) -> None:
        if self._worker is None or self._queue is None:
            return

        self._stopped = True

        try:
            await asyncio.wait_for(self._queue.join(), timeout=timeout)
        except asyncio.TimeoutError:
            LOGGER.warning(
                "Observatory adapter stop timed out; cancelling pending events"
            )

        self._worker.cancel()
        await asyncio.gather(self._worker, return_exceptions=True)

        await self.transport.close()

        self._worker = None
        self._loop = None

    async def observe(
        self,
        *,
        category: str,
        type: str,
        subject_id: str,
        payload: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        epistemic_status: str = "observed",
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._stopped or self._queue is None:
            return

        try:
            merged_provenance = {
                "environment": self.settings.environment,
                "adapter": "tiannara-runtime-adapter",
            }

            if provenance:
                merged_provenance.update(provenance)

            event = build_event(
                source=self.settings.source,
                category=category,
                type=type,
                subject_id=subject_id,
                payload=payload,
                severity=severity,
                epistemic_status=epistemic_status,
                correlation_id=correlation_id,
                causation_id=causation_id,
                evidence_refs=evidence_refs,
                provenance=merged_provenance,
            )

            if self.settings.redaction_enabled:
                event["payload"] = redact(event["payload"])
                event["provenance"] = redact(event["provenance"])

            self._queue.put_nowait(event)

        except asyncio.QueueFull:
            self.dropped_events += 1
            LOGGER.warning(
                "Observatory adapter queue full; dropping event type=%s subject=%s",
                type,
                subject_id,
            )

        except ValueError:
            LOGGER.exception(
                "Failed to construct Observatory event type=%s subject=%s",
                type,
                subject_id,
            )

    def observe_blocking(
        self,
        *,
        category: str,
        type: str,
        subject_id: str,
        payload: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        epistemic_status: str = "observed",
        correlation_id: Optional[str] = None,
        causation_id: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._loop is None or self._loop.is_closed():
            return

        try:
            asyncio.run_coroutine_threadsafe(
                self.observe(
                    category=category,
                    type=type,
                    subject_id=subject_id,
                    payload=payload,
                    severity=severity,
                    epistemic_status=epistemic_status,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                    evidence_refs=evidence_refs,
                    provenance=provenance,
                ),
                self._loop,
            )
        except RuntimeError:
            return

    async def process_started(
        self,
        process_name: str,
        supervisor: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "process": process_name,
            "supervisor": supervisor,
            "summary": f"{process_name} started",
            **(metadata or {}),
        }

        await self.observe(
            category="runtime",
            type="process_started",
            subject_id=process_name,
            payload=payload,
            severity="info",
        )

    async def process_stopped(
        self,
        process_name: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "process": process_name,
            "reason": reason,
            "summary": f"{process_name} stopped",
            **(metadata or {}),
        }

        await self.observe(
            category="runtime",
            type="process_stopped",
            subject_id=process_name,
            payload=payload,
            severity="info",
        )

    async def process_restarted(
        self,
        process_name: str,
        restart_count: Optional[int] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "process": process_name,
            "restart_count": restart_count,
            "reason": reason,
            "summary": f"{process_name} restarted",
            **(metadata or {}),
        }

        await self.observe(
            category="runtime",
            type="process_restarted",
            subject_id=process_name,
            payload=payload,
            severity="warning",
        )

    async def process_crashed(
        self,
        process_name: str,
        error_type: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "process": process_name,
            "error_type": error_type,
            "reason": reason,
            "summary": f"{process_name} crashed",
            **(metadata or {}),
        }

        await self.observe(
            category="runtime",
            type="process_crashed",
            subject_id=process_name,
            payload=payload,
            severity="error",
        )

    async def metric(
        self,
        metric_name: str,
        value: Any,
        unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "metric": metric_name,
            "value": value,
            "unit": unit,
            **(metadata or {}),
        }

        await self.observe(
            category="runtime",
            type="metric",
            subject_id=metric_name,
            payload=payload,
            severity="info",
        )

    async def log_event(
        self,
        subject_id: str,
        message: str,
        level: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        severity = self._severity_from_log_level(level)

        payload = {
            "message": message,
            "level": level,
            "summary": message,
            **(metadata or {}),
        }

        await self.observe(
            category="runtime",
            type="log",
            subject_id=subject_id,
            payload=payload,
            severity=severity,
        )

    async def _run(self) -> None:
        assert self._queue is not None

        while True:
            event = await self._queue.get()

            try:
                await self._send_with_retry(event)
                self.sent_events += 1

            except PermanentTransportError as exc:
                self.failed_events += 1
                self._write_failure(event, str(exc))

            except Exception as exc:
                self.failed_events += 1
                self._write_failure(event, f"unexpected error: {exc}")

            finally:
                self._queue.task_done()

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
                        "observatory delivery failed after retries"
                    ) from exc

                await asyncio.sleep(delay)
                delay = min(delay * 2, self.settings.max_retry_delay_seconds)

            except PermanentTransportError:
                raise

    def _write_failure(self, event: Dict[str, Any], reason: str) -> None:
        if self._failure_path is None:
            return

        try:
            self._failure_path.parent.mkdir(parents=True, exist_ok=True)

            record = {
                "failed_at": utc_now().isoformat(),
                "reason": reason,
                "event": event,
            }

            with self._failure_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True, default=str))
                handle.write("\n")

        except Exception:
            LOGGER.exception("Failed to write Observatory adapter failure record")

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
```

---

# 8. Python logging handler

**`observatory/adapters/tiannara/logging_handler.py`**

```python
from __future__ import annotations

import logging
from typing import Optional

from .runtime_adapter import TiannaraRuntimeAdapter


class ObservatoryRuntimeLogHandler(logging.Handler):
    """
    Logging handler that forwards selected Tiannara logs to the Observatory.

    This handler is non-blocking and fail-safe. If the Observatory adapter
    is unavailable, logging must not crash the runtime.
    """

    def __init__(
        self,
        adapter: TiannaraRuntimeAdapter,
        subject: str = "Tiannara.Runtime",
        level: int = logging.INFO,
    ) -> None:
        super().__init__(level=level)
        self.adapter = adapter
        self.subject = subject

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = {
                "logger": record.name,
                "level": record.levelname,
                "message": record.getMessage(),
            }

            if record.exc_info:
                exc_type, exc_value, _ = record.exc_info

                if exc_type is not None:
                    payload["error_type"] = exc_type.__name__

                if exc_value is not None:
                    payload["error_summary"] = str(exc_value)

            self.adapter.observe_blocking(
                category="runtime",
                type="log",
                subject_id=self.subject,
                payload=payload,
                severity=self._map_severity(record.levelno),
            )

        except Exception:
            self.handleError(record)

    def _map_severity(self, levelno: int) -> str:
        if levelno >= logging.CRITICAL:
            return "fatal"

        if levelno >= logging.ERROR:
            return "error"

        if levelno >= logging.WARNING:
            return "warning"

        if levelno >= logging.INFO:
            return "info"

        return "debug"
```

---

# 9. Package exports

**`observatory/adapters/tiannara/__init__.py`**

```python
from .config import TiannaraAdapterSettings, get_adapter_settings
from .logging_handler import ObservatoryRuntimeLogHandler
from .runtime_adapter import TiannaraRuntimeAdapter

__all__ = [
    "TiannaraAdapterSettings",
    "get_adapter_settings",
    "ObservatoryRuntimeLogHandler",
    "TiannaraRuntimeAdapter",
]
```

**`observatory/adapters/__init__.py`**

```python
```

This can be empty.

---

# 10. Tiannara runtime integration example

This shows how to attach the adapter to a Python/FastAPI Tiannara application.

```python
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from observatory.adapters.tiannara import (
    ObservatoryRuntimeLogHandler,
    TiannaraRuntimeAdapter,
    get_adapter_settings,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_adapter_settings()
    adapter = TiannaraRuntimeAdapter(settings)

    await adapter.start()

    app.state.observatory_adapter = adapter

    tiannara_logger = logging.getLogger("tiannara")
    handler = ObservatoryRuntimeLogHandler(adapter)
    tiannara_logger.addHandler(handler)

    await adapter.process_started(
        process_name="Tiannara.Application",
        supervisor="Tiannara.Runtime",
        metadata={
            "service": "tiannara",
            "mode": settings.environment,
        },
    )

    yield

    await adapter.process_stopped(
        process_name="Tiannara.Application",
        reason="application_shutdown",
    )

    await adapter.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Tiannara",
        lifespan=lifespan,
    )

    return app


app = create_app()
```

---

# 11. Emitting custom runtime events

Inside Tiannara services:

```python
adapter = request.app.state.observatory_adapter

await adapter.observe(
    category="runtime",
    type="task_created",
    subject_id="TASK-001",
    payload={
        "task_id": "TASK-001",
        "priority": "HIGH",
        "summary": "Task TASK-001 created",
    },
    severity="info",
)
```

For metrics:

```python
await adapter.metric(
    metric_name="messages_per_sec",
    value=4.8,
    unit="msg/s",
)
```

For crashes:

```python
await adapter.process_crashed(
    process_name="AgencyLoop",
    error_type="RuntimeError",
    reason="unexpected exception",
)
```

---

# 12. Adapter guarantees

This adapter guarantees:

```text
non-blocking observation
secret redaction
retry with bounded backoff
failure isolation
no runtime mutation
no command issuance
no deployment
no production authority
no evolution execution
```

If the Observatory is unavailable, the Tiannara runtime continues operating.

The adapter may drop events under sustained backpressure, but it records internal counters:

```text
sent_events
dropped_events
failed_events
```

Failed events are written to:

```text
observatory_adapter_failures.jsonl
```

assuming the default configuration.

---

# 13. Constitutional alignment

This adapter respects the platform constitution:

```text
ISR remains untouched.
Observatory is a production subsystem, not a code generator.
The adapter is replaceable through plugin boundaries.
Python is used because it is the current native runtime.
No framework becomes the platform core.
Observability is designed in from the first version.
Security redaction is applied before transport.
The adapter observes; it does not decide.
```

---

# 14. Next required step

The next step is the **batch ingestion endpoint** on the Observatory backend:

```text
POST /observatory/events/batch
```

That will allow the adapter to send multiple events in one request while preserving idempotency and event-hash integrity.

After that, add:

```text
adapter integration tests
contract tests against /observatory/events
failure/retry tests
redaction tests
runtime supervisor hooks
metric collection hooks
```