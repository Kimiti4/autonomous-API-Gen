Yes — that correction is architecturally right.

The Observatory should be implemented in the **native runtime of the actual system**. If the governed Tiannara implementation is Python, then the Observatory backend should also be Python unless there is explicit evidence that another runtime is required.

That preserves:

```text
ISR / architectural core
        ↓
Python Tiannara runtime
        ↓
Python Observatory backend
        ↓
TypeScript/React frontend
```

and avoids introducing an unnecessary second runtime boundary.

Below is the **Python backend foundation** for the Observatory.

It implements:

```text
canonical event model
epistemic typing
SQLite-backed event persistence
projection read models
governance command boundary
async event bus
FastAPI read/write API
server-sent event stream
secret redaction
authorization boundary
trace / explain endpoints
```

This is not a dashboard stub. It is the backend control surface.

---

# 1. Backend structure

Create this structure:

```text
observatory/
├── __init__.py
└── backend/
    ├── __init__.py
    ├── main.py
    ├── config.py
    ├── domain.py
    ├── store.py
    ├── projections.py
    ├── bus.py
    ├── governance.py
    ├── gateway.py
    └── api/
        ├── __init__.py
        ├── deps.py
        └── routes.py
```

---

# 2. Python dependencies

**`requirements.txt`**

```text
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
pydantic>=2.7.0
```

---

# 3. Backend domain model

**`observatory/backend/domain.py`**

```python
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EpistemicStatus(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNKNOWN = "unknown"
    CONTRADICTION = "contradiction"


class Severity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class EventCategory(str, Enum):
    RUNTIME = "runtime"
    EVIDENCE = "evidence"
    EVOLUTION = "evolution"
    GOVERNANCE = "governance"
    KNOWLEDGE = "knowledge"


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

    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError as exc:
            raise ValueError(f"invalid timestamp: {value}") from exc

    raise ValueError(f"invalid timestamp type: {type(value)!r}")


class Event(BaseModel):
    id: str
    timestamp: datetime
    source: str
    category: EventCategory
    type: str
    subject_id: str
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    epistemic_status: EpistemicStatus
    authorization: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    severity: Severity


class EventInput(BaseModel):
    id: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: str
    category: EventCategory
    type: str
    subject_id: str
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    authorization: Optional[str] = None
    evidence_refs: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    severity: Severity = Severity.INFO


class Actor(BaseModel):
    id: str
    role: str
    clearance: Optional[str] = None


class CommandRequest(BaseModel):
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)


def event_hash(event: Event) -> str:
    return sha256_hex(canonical_json(event.model_dump(mode="json")))


def generate_event_id(
    *,
    category: EventCategory,
    source: str,
    type: str,
    subject_id: str,
    payload: Dict[str, Any],
    timestamp: datetime,
) -> str:
    basis = canonical_json(
        {
            "category": category.value,
            "source": source,
            "type": type,
            "subject_id": subject_id,
            "payload": payload,
            "timestamp": timestamp.isoformat(),
        }
    )
    digest = sha256_hex(basis)
    return f"evt-{category.value}-{digest[:24]}"


def new_event(
    *,
    category: EventCategory,
    source: str,
    type: str,
    subject_id: str,
    payload: Optional[Dict[str, Any]] = None,
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED,
    severity: Severity = Severity.INFO,
    evidence_refs: Optional[List[str]] = None,
    provenance: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None,
    id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
    authorization: Optional[str] = None,
) -> Event:
    if not source:
        raise ValueError("event source is required")
    if not type:
        raise ValueError("event type is required")
    if not subject_id:
        raise ValueError("event subject_id is required")

    resolved_timestamp = parse_timestamp(timestamp)
    resolved_payload = dict(payload or {})

    resolved_id = id or generate_event_id(
        category=category,
        source=source,
        type=type,
        subject_id=subject_id,
        payload=resolved_payload,
        timestamp=resolved_timestamp,
    )

    return Event(
        id=resolved_id,
        timestamp=resolved_timestamp,
        source=source,
        category=category,
        type=type,
        subject_id=subject_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        payload=resolved_payload,
        epistemic_status=epistemic_status,
        authorization=authorization,
        evidence_refs=list(evidence_refs or []),
        provenance=dict(provenance or {}),
        severity=severity,
    )


def new_runtime_event(**kwargs: Any) -> Event:
    return new_event(category=EventCategory.RUNTIME, **kwargs)


def new_evolution_event(**kwargs: Any) -> Event:
    return new_event(category=EventCategory.EVOLUTION, **kwargs)


def new_knowledge_event(**kwargs: Any) -> Event:
    return new_event(category=EventCategory.KNOWLEDGE, **kwargs)


def new_evidence_event(
    *,
    source: str,
    subject_id: str,
    claim: str,
    result: Any,
    scope: Optional[List[str]] = None,
    not_proven: Optional[List[str]] = None,
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED,
    type: str = "evidence_recorded",
    payload: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Event:
    if not claim:
        raise ValueError("evidence claim is required")
    if result is None:
        raise ValueError("evidence result is required")

    resolved_payload = dict(payload or {})
    resolved_payload.update(
        {
            "claim": claim,
            "result": result,
            "scope": list(scope or []),
            "not_proven": list(not_proven or []),
        }
    )

    return new_event(
        category=EventCategory.EVIDENCE,
        source=source,
        type=type,
        subject_id=subject_id,
        payload=resolved_payload,
        epistemic_status=epistemic_status,
        **kwargs,
    )


def new_governance_event(
    *,
    source: str,
    type: str,
    subject_id: str = "GOVERNANCE",
    reason: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Event:
    resolved_payload = dict(payload or {})

    if type == "command_rejected" and not reason:
        raise ValueError("command_rejected events require a reason")

    if reason is not None:
        resolved_payload["reason"] = reason

    return new_event(
        category=EventCategory.GOVERNANCE,
        source=source,
        type=type,
        subject_id=subject_id,
        payload=resolved_payload,
        **kwargs,
    )


def event_from_input(event_input: EventInput) -> Event:
    return new_event(
        category=event_input.category,
        source=event_input.source,
        type=event_input.type,
        subject_id=event_input.subject_id,
        payload=event_input.payload,
        epistemic_status=event_input.epistemic_status,
        severity=event_input.severity,
        evidence_refs=event_input.evidence_refs,
        provenance=event_input.provenance,
        timestamp=event_input.timestamp,
        id=event_input.id,
        correlation_id=event_input.correlation_id,
        causation_id=event_input.causation_id,
        authorization=event_input.authorization,
    )
```

---

# 4. Configuration

**`observatory/backend/config.py`**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Tuple


@dataclass(frozen=True)
class Settings:
    db_path: str
    api_token: Optional[str]
    cors_origins: Tuple[str, ...]


@lru_cache
def get_settings() -> Settings:
    raw_origins = os.getenv("OBSERVATORY_CORS_ORIGINS", "")
    origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())

    return Settings(
        db_path=os.getenv("OBSERVATORY_DB_PATH", "observatory.sqlite3"),
        api_token=os.getenv("OBSERVATORY_API_TOKEN") or None,
        cors_origins=origins,
    )
```

---

# 5. SQLite event store

**`observatory/backend/store.py`**

```python
from __future__ import annotations

import json
import sqlite3
import threading
from typing import List, Optional, Union

from .domain import Event, EventCategory, event_hash


class StoreIntegrityError(Exception):
    pass


class SqliteEventStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")

    def init(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    event_hash TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    type TEXT NOT NULL,
                    subject_id TEXT NOT NULL,
                    correlation_id TEXT,
                    causation_id TEXT,
                    payload TEXT NOT NULL,
                    epistemic_status TEXT NOT NULL,
                    authorization TEXT,
                    evidence_refs TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    severity TEXT NOT NULL
                )
                """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS events_subject_idx
                ON events (subject_id, timestamp)
                """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS events_category_idx
                ON events (category, timestamp)
                """
            )

            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS events_timestamp_idx
                ON events (timestamp)
                """
            )

            self._conn.commit()

    def append(self, event: Event) -> bool:
        computed_hash = event_hash(event)
        dump = event.model_dump(mode="json")

        with self._lock:
            existing = self._conn.execute(
                "SELECT event_hash FROM events WHERE id = ?",
                (event.id,),
            ).fetchone()

            if existing is not None:
                if existing["event_hash"] != computed_hash:
                    raise StoreIntegrityError(
                        f"event id {event.id} already exists with a different hash"
                    )
                return False

            self._conn.execute(
                """
                INSERT INTO events (
                    id,
                    event_hash,
                    timestamp,
                    source,
                    category,
                    type,
                    subject_id,
                    correlation_id,
                    causation_id,
                    payload,
                    epistemic_status,
                    authorization,
                    evidence_refs,
                    provenance,
                    severity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    computed_hash,
                    event.timestamp.isoformat(),
                    dump["source"],
                    dump["category"],
                    dump["type"],
                    dump["subject_id"],
                    dump["correlation_id"],
                    dump["causation_id"],
                    json.dumps(dump["payload"], sort_keys=True, default=str),
                    dump["epistemic_status"],
                    dump["authorization"],
                    json.dumps(dump["evidence_refs"], sort_keys=True, default=str),
                    json.dumps(dump["provenance"], sort_keys=True, default=str),
                    dump["severity"],
                ),
            )
            self._conn.commit()
            return True

    def get_event(self, event_id: str) -> Optional[Event]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_event(row)

    def events_by_subject(self, subject_id: str, limit: int = 1000) -> List[Event]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT *
                FROM events
                WHERE subject_id = ?
                ORDER BY timestamp ASC, id ASC
                LIMIT ?
                """,
                (subject_id, limit),
            ).fetchall()

        return [self._row_to_event(row) for row in rows]

    def events_by_category(
        self,
        category: Union[EventCategory, str],
        limit: int = 1000,
    ) -> List[Event]:
        resolved_category = (
            category.value if isinstance(category, EventCategory) else str(category)
        )

        with self._lock:
            rows = self._conn.execute(
                """
                SELECT *
                FROM events
                WHERE category = ?
                ORDER BY timestamp ASC, id ASC
                LIMIT ?
                """,
                (resolved_category, limit),
            ).fetchall()

        return [self._row_to_event(row) for row in rows]

    def recent_events(self, limit: int = 100, descending: bool = False) -> List[Event]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT *
                FROM events
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        events = [self._row_to_event(row) for row in rows]

        if descending:
            return events

        return list(reversed(events))

    def count_events(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()
            return int(row["count"])

    def count_events_by_category(self, category: Union[EventCategory, str]) -> int:
        resolved_category = (
            category.value if isinstance(category, EventCategory) else str(category)
        )

        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS count FROM events WHERE category = ?",
                (resolved_category,),
            ).fetchone()
            return int(row["count"])

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        return Event.model_validate(
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "source": row["source"],
                "category": row["category"],
                "type": row["type"],
                "subject_id": row["subject_id"],
                "correlation_id": row["correlation_id"],
                "causation_id": row["causation_id"],
                "payload": json.loads(row["payload"]),
                "epistemic_status": row["epistemic_status"],
                "authorization": row["authorization"],
                "evidence_refs": json.loads(row["evidence_refs"]),
                "provenance": json.loads(row["provenance"]),
                "severity": row["severity"],
            }
        )
```

---

# 6. Async event bus

**`observatory/backend/bus.py`**

```python
from __future__ import annotations

import asyncio
from typing import Set

from .domain import Event


class AsyncEventBus:
    def __init__(self, max_queue_size: int = 1000) -> None:
        self._subscribers: Set[asyncio.Queue] = set()
        self._max_queue_size = max_queue_size

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue_size)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: Event) -> None:
        for queue in list(self._subscribers):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                continue
```

---

# 7. Projections

**`observatory/backend/projections.py`**

```python
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .domain import EpistemicStatus, Event, EventCategory, Severity

DEFAULT_AUTHORITY = {
    "interpretation": "granted",
    "evolution": "definition_only",
    "implementation": "none",
    "runtime": "none",
    "deployment": "none",
    "production": "none",
    "governance": "granted",
}

EVOLUTION_STAGES = [
    "requirement_parsed",
    "isr_consulted",
    "constraints_derived",
    "candidate_generated",
    "static_validation",
    "runtime_validation",
    "evidence_certification",
]

SUCCESS_VALUES = {
    "success",
    "pass",
    "ok",
    "completed",
    "done",
}


def sort_asc(events: List[Event]) -> List[Event]:
    return sorted(events, key=lambda event: event.timestamp)


def latest_event(events: List[Event]) -> Optional[Event]:
    if not events:
        return None
    return max(events, key=lambda event: event.timestamp)


def payload_get(payload: Dict[str, Any], key: str, default: Any = None) -> Any:
    if payload is None:
        return default

    if key in payload:
        return payload[key]

    string_key = str(key)
    if string_key in payload:
        return payload[string_key]

    return default


def result_is_ok(value: Any) -> bool:
    if value is None:
        return True

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in SUCCESS_VALUES


def count_epistemic(events: List[Event]) -> Dict[str, int]:
    counts = {
        EpistemicStatus.OBSERVED.value: 0,
        EpistemicStatus.INFERRED.value: 0,
        EpistemicStatus.UNKNOWN.value: 0,
        EpistemicStatus.CONTRADICTION.value: 0,
    }

    for event in events:
        counts[event.epistemic_status.value] += 1

    return counts


def build_runtime_state(events: List[Event]) -> Dict[str, Any]:
    runtime_events = sort_asc(
        [event for event in events if event.category == EventCategory.RUNTIME]
    )

    process_started = count_type(runtime_events, "process_started")
    process_stopped = count_type(runtime_events, "process_stopped")
    restart_count = count_type(runtime_events, "process_restarted")
    supervisors = count_type(runtime_events, "supervisor_started")

    processes = max(process_started - process_stopped, 0)
    messages_per_sec = latest_metric(runtime_events, "messages_per_sec")
    memory_total = latest_metric(runtime_events, "memory_total")
    health = derive_runtime_health(runtime_events)
    latest = latest_event(runtime_events)

    return {
        "processes": processes,
        "supervisors": supervisors,
        "messages_per_sec": messages_per_sec,
        "memory_total": memory_total,
        "restart_count": restart_count,
        "health": health,
        "updated_at": latest.timestamp if latest else None,
    }


def count_type(events: List[Event], type: str) -> int:
    return sum(1 for event in events if event.type == type)


def latest_metric(events: List[Event], key: str) -> Any:
    metric_events = [
        event
        for event in events
        if event.type == "metric" and payload_get(event.payload, key) is not None
    ]

    latest = latest_event(metric_events)
    if latest is None:
        return "not_measured"

    return payload_get(latest.payload, key)


def derive_runtime_health(events: List[Event]) -> str:
    if not events:
        return "unknown"

    degraded = any(
        event.severity in {Severity.ERROR, Severity.FATAL}
        or event.type in {"process_crashed", "supervisor_crashed", "runtime_failure"}
        for event in events
    )

    return "degraded" if degraded else "green"


def build_evolution_state(evolution_id: str, events: List[Event]) -> Dict[str, Any]:
    relevant = sort_asc(
        [
            event
            for event in events
            if event.subject_id == evolution_id
        ]
    )

    pipeline = build_pipeline(relevant)

    return {
        "evolution_id": evolution_id,
        "status": derive_evolution_status(relevant, pipeline),
        "epistemic_state": derive_epistemic_state(relevant),
        "capability_check": derive_capability_check(relevant),
        "pipeline": pipeline,
        "decision": derive_decision(relevant),
        "authorization": derive_authorization(relevant),
        "unknowns": derive_unknowns(relevant),
        "contradictions": derive_contradictions(relevant),
        "updated_at": latest_event(relevant).timestamp if relevant else None,
    }


def build_pipeline(events: List[Event]) -> List[Dict[str, str]]:
    blocked = any(event.type == "evolution_blocked" for event in events)

    pipeline = []

    for stage in EVOLUTION_STAGES:
        if stage_failed(events, stage):
            status = "failed"
        elif blocked and not stage_done(events, stage):
            status = "blocked"
        elif stage_done(events, stage):
            status = "done"
        else:
            status = "pending"

        pipeline.append(
            {
                "stage": stage,
                "status": status,
            }
        )

    return mark_current_stage(pipeline)


def stage_done(events: List[Event], stage: str) -> bool:
    for event in events:
        if event.type == stage and result_is_ok(payload_get(event.payload, "result")):
            return True

        if (
            event.type == "stage_completed"
            and payload_get(event.payload, "stage") == stage
            and result_is_ok(payload_get(event.payload, "result"))
        ):
            return True

    return False


def stage_failed(events: List[Event], stage: str) -> bool:
    return any(
        event.type == "stage_failed" and payload_get(event.payload, "stage") == stage
        for event in events
    )


def mark_current_stage(pipeline: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if any(item["status"] in {"failed", "blocked"} for item in pipeline):
        return pipeline

    current_marked = False

    for item in pipeline:
        if item["status"] == "pending" and not current_marked:
            item["status"] = "current"
            current_marked = True

    return pipeline


def derive_evolution_status(events: List[Event], pipeline: List[Dict[str, str]]) -> str:
    if not events:
        return "unknown"

    if any(event.type == "evolution_blocked" for event in events):
        return "blocked"

    if any(item["status"] == "failed" for item in pipeline):
        return "blocked"

    if all(item["status"] == "done" for item in pipeline):
        return "complete"

    return "in_progress"


def derive_epistemic_state(events: List[Event]) -> Dict[str, int]:
    evidence_events = [event for event in events if event.category == EventCategory.EVIDENCE]
    return count_epistemic(evidence_events)


def derive_capability_check(events: List[Event]) -> Dict[str, str]:
    capability_state = {
        "generation": "unknown",
        "validation": "unknown",
        "runtime": "unknown",
        "production": "unknown",
    }

    for event in events:
        if event.type not in {"capability_check", "capability_assessed"}:
            continue

        capability = str(payload_get(event.payload, "capability", "")).strip().lower()
        status = str(payload_get(event.payload, "status", "unknown")).strip().lower()

        if capability in capability_state:
            capability_state[capability] = status

    return capability_state


def derive_decision(events: List[Event]) -> str:
    decision_events = [
        event
        for event in events
        if event.type
        in {
            "decision_recorded",
            "evolution_decision",
            "evolution_advanced",
            "evolution_held",
            "evolution_blocked",
        }
    ]

    latest = latest_event(decision_events)
    if latest is None:
        return "unknown"

    payload_decision = payload_get(latest.payload, "decision")
    if payload_decision is not None:
        return str(payload_decision)

    if latest.type == "evolution_advanced":
        return "advanced"

    if latest.type == "evolution_held":
        return "held"

    if latest.type == "evolution_blocked":
        return "blocked"

    return "recorded"


def derive_authorization(events: List[Event]) -> Dict[str, str]:
    authority = dict(DEFAULT_AUTHORITY)

    authorization_events = [
        event for event in events if event.type == "authorization_updated"
    ]

    latest = latest_event(authorization_events)
    if latest is None:
        return authority

    raw_authority = payload_get(latest.payload, "authority", {})
    if not isinstance(raw_authority, dict):
        return authority

    normalized = {
        str(key).strip().lower(): str(value).strip().lower()
        for key, value in raw_authority.items()
    }

    for key in DEFAULT_AUTHORITY:
        if key in normalized:
            authority[key] = normalized[key]

    return authority


def derive_unknowns(events: List[Event]) -> List[str]:
    unknowns = set()

    for event in events:
        if event.epistemic_status == EpistemicStatus.UNKNOWN:
            unknown_id = payload_get(event.payload, "unknown_id", event.subject_id)
            unknowns.add(str(unknown_id))

    return sorted(unknowns)


def derive_contradictions(events: List[Event]) -> List[str]:
    contradictions = set()

    for event in events:
        if event.epistemic_status == EpistemicStatus.CONTRADICTION:
            contradiction_id = payload_get(
                event.payload,
                "contradiction_id",
                event.subject_id,
            )
            contradictions.add(str(contradiction_id))

    return sorted(contradictions)


def build_evidence_state(events: List[Event]) -> List[Dict[str, Any]]:
    evidence_events = sort_asc(
        [event for event in events if event.category == EventCategory.EVIDENCE]
    )

    grouped: Dict[str, List[Event]] = {}
    for event in evidence_events:
        grouped.setdefault(event.subject_id, []).append(event)

    records = []

    for evidence_id, grouped_events in grouped.items():
        records.append(build_evidence_record(evidence_id, grouped_events))

    return sorted(records, key=lambda record: record["evidence_id"])


def build_evidence_record(evidence_id: str, events: List[Event]) -> Dict[str, Any]:
    latest = latest_event(events)
    assert latest is not None

    claim = str(payload_get(latest.payload, "claim", "unspecified"))

    if latest.epistemic_status == EpistemicStatus.CONTRADICTION:
        result = "contradiction"
    else:
        result = payload_get(latest.payload, "result", "unknown")

    scope = payload_get(latest.payload, "scope", [])
    not_proven = payload_get(latest.payload, "not_proven", [])

    provenance = dict(latest.provenance or {})

    payload_provenance = payload_get(latest.payload, "provenance", {})
    if isinstance(payload_provenance, dict):
        provenance.update(payload_provenance)

    for event in events:
        if event.type != "provenance_verified":
            continue

        checks = payload_get(event.payload, "checks", {})
        if isinstance(checks, dict):
            provenance.update(checks)

    return {
        "evidence_id": evidence_id,
        "epistemic_status": latest.epistemic_status.value,
        "claim": claim,
        "result": result,
        "scope": scope,
        "not_proven": not_proven,
        "provenance": provenance,
        "observed_at": latest.timestamp,
    }


def get_evidence(events: List[Event], evidence_id: str) -> Optional[Dict[str, Any]]:
    for record in build_evidence_state(events):
        if record["evidence_id"] == evidence_id:
            return record

    return None


def build_governance_state(events: List[Event]) -> Dict[str, Any]:
    governance_events = sort_asc(
        [event for event in events if event.category == EventCategory.GOVERNANCE]
    )

    authority = dict(DEFAULT_AUTHORITY)
    gates: Dict[str, str] = {}
    safe_mode = "unknown"

    commands = {
        "requested": 0,
        "accepted": 0,
        "rejected": 0,
    }

    for event in governance_events:
        if event.type == "authority_updated":
            raw_authority = payload_get(event.payload, "authority", {})
            if isinstance(raw_authority, dict):
                normalized = {
                    str(key).strip().lower(): str(value).strip().lower()
                    for key, value in raw_authority.items()
                }

                for key in DEFAULT_AUTHORITY:
                    if key in normalized:
                        authority[key] = normalized[key]

        elif event.type == "gate_updated":
            gate = payload_get(event.payload, "gate")
            status = payload_get(event.payload, "status", "unknown")

            if gate is not None:
                gates[str(gate)] = str(status)

        elif event.type == "safe_mode_enabled":
            safe_mode = "enabled"

        elif event.type == "safe_mode_disabled":
            safe_mode = "disabled"

        elif event.type == "command_requested":
            commands["requested"] += 1

        elif event.type == "command_accepted":
            commands["accepted"] += 1

        elif event.type == "command_rejected":
            commands["rejected"] += 1

    active_gates = [
        {
            "gate": gate,
            "status": status,
        }
        for gate, status in sorted(gates.items())
    ]

    return {
        "current_authority": authority,
        "active_gates": active_gates,
        "safe_mode": safe_mode,
        "human_controls": [
            "safe_mode",
            "stop",
            "restart",
            "request_authorization",
        ],
        "command_activity": commands,
    }


def build_knowledge_state(events: List[Event]) -> List[Dict[str, Any]]:
    relevant = sort_asc(
        [
            event
            for event in events
            if event.category in {EventCategory.KNOWLEDGE, EventCategory.EVIDENCE}
        ]
    )

    grouped: Dict[str, List[Event]] = {}
    for event in relevant:
        grouped.setdefault(event.subject_id, []).append(event)

    records = []

    for subject_id, grouped_events in grouped.items():
        latest = latest_event(grouped_events)
        assert latest is not None

        records.append(
            {
                "subject_id": subject_id,
                "epistemic_state": count_epistemic(grouped_events),
                "latest_status": latest.epistemic_status.value,
                "updated_at": latest.timestamp,
            }
        )

    return sorted(records, key=lambda record: record["subject_id"])


def get_knowledge(events: List[Event], subject_id: str) -> Optional[Dict[str, Any]]:
    for record in build_knowledge_state(events):
        if record["subject_id"] == subject_id:
            return record

    return None


def build_requirement_state(requirement_id: str, events: List[Event]) -> Optional[Dict[str, Any]]:
    relevant = sort_asc([event for event in events if event.subject_id == requirement_id])

    if not relevant:
        return None

    latest = latest_event(relevant)
    assert latest is not None

    return {
        "requirement_id": requirement_id,
        "status": payload_get(latest.payload, "status", latest.epistemic_status.value),
        "epistemic_state": count_epistemic(relevant),
        "evidence_refs": collect_evidence_refs(relevant),
        "related_capabilities": collect_payload_list(relevant, "capabilities"),
        "related_evolutions": collect_payload_list(relevant, "evolutions"),
        "unknown_dependencies": collect_payload_list(relevant, "unknown_dependencies"),
        "updated_at": latest.timestamp,
    }


def build_capability_state(capability_id: str, events: List[Event]) -> Optional[Dict[str, Any]]:
    relevant = sort_asc([event for event in events if event.subject_id == capability_id])

    if not relevant:
        return None

    latest = latest_event(relevant)
    assert latest is not None

    return {
        "capability_id": capability_id,
        "status": payload_get(latest.payload, "status", latest.epistemic_status.value),
        "epistemic_state": count_epistemic(relevant),
        "evidence_refs": collect_evidence_refs(relevant),
        "related_requirements": collect_payload_list(relevant, "requirements"),
        "related_evolutions": collect_payload_list(relevant, "evolutions"),
        "updated_at": latest.timestamp,
    }


def collect_evidence_refs(events: List[Event]) -> List[str]:
    refs = set()

    for event in events:
        for ref in event.evidence_refs:
            refs.add(str(ref))

    return sorted(refs)


def collect_payload_list(events: List[Event], key: str) -> List[str]:
    values: List[str] = []

    for event in events:
        value = payload_get(event.payload, key, [])

        if isinstance(value, list):
            values.extend(str(item) for item in value if item is not None)
        elif value is not None:
            values.append(str(value))

    return sorted(set(values))
```

---

# 8. Governance boundary

**`observatory/backend/governance.py`**

```python
from __future__ import annotations

from typing import Dict, List

from .domain import Actor

READ_ACTIONS: List[str] = [
    "view_dashboard",
    "view_overview",
    "view_runtime",
    "view_evolution",
    "view_evidence",
    "view_requirement",
    "view_capability",
    "view_knowledge",
    "view_governance",
    "trace",
    "explain",
]

COMMAND_ACTIONS: List[str] = [
    "request_authorization",
    "request_evolution_definition",
    "request_implementation",
    "request_runtime",
    "request_production_deploy",
    "safe_mode_enable",
    "safe_mode_disable",
    "stop_runtime",
    "restart_runtime",
]


class AuthorizationError(Exception):
    pass


class GovernanceBoundary:
    def authorize(
        self,
        action: str,
        actor: Actor,
        authority: Dict[str, str],
    ) -> None:
        if action not in READ_ACTIONS and action not in COMMAND_ACTIONS:
            raise AuthorizationError("unsupported_action")

        self._check_actor(action, actor)
        self._check_authority(action, authority)

    def _check_actor(self, action: str, actor: Actor) -> None:
        role = actor.role or "observer"
        clearance = actor.clearance or role

        if action in READ_ACTIONS:
            if role in {"observer", "operator", "architect", "admin", "system"}:
                return
            raise AuthorizationError("unauthorized")

        if action in COMMAND_ACTIONS:
            if clearance in {"operator", "architect", "admin"}:
                return
            raise AuthorizationError("unauthorized")

        raise AuthorizationError("unsupported_action")

    def _check_authority(self, action: str, authority: Dict[str, str]) -> None:
        if action == "request_authorization":
            if self._authorized(authority.get("governance"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")

        if action == "request_evolution_definition":
            if self._authorized(authority.get("evolution"), {"granted", "definition_only"}):
                return
            raise AuthorizationError("blocked_by_constitution")

        if action == "request_implementation":
            if self._authorized(authority.get("implementation"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")

        if action == "request_runtime":
            if self._authorized(authority.get("runtime"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")

        if action == "request_production_deploy":
            if self._authorized(authority.get("production"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")

        if action in {"safe_mode_enable", "safe_mode_disable"}:
            if self._authorized(authority.get("governance"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")

        if action in {"stop_runtime", "restart_runtime"}:
            if self._authorized(authority.get("runtime"), {"granted"}):
                return
            raise AuthorizationError("blocked_by_constitution")

        raise AuthorizationError("unsupported_action")

    def _authorized(self, value: str | None, allowed_values: set[str]) -> bool:
        return value in allowed_values
```

---

# 9. Observatory gateway

**`observatory/backend/gateway.py`**

```python
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from .bus import AsyncEventBus
from .domain import (
    Actor,
    CommandRequest,
    Event,
    EventCategory,
    canonical_json,
    new_governance_event,
    sha256_hex,
    utc_now,
)
from .governance import COMMAND_ACTIONS, AuthorizationError, GovernanceBoundary
from .store import SqliteEventStore, StoreIntegrityError
from . import projections


class ObservatoryError(Exception):
    pass


class NotFoundError(ObservatoryError):
    pass


SECRET_KEY_MARKERS = (
    "password",
    "secret",
    "token",
    "credential",
    "api_key",
    "apikey",
    "private_key",
    "session",
)


class ObservatoryGateway:
    def __init__(
        self,
        store: SqliteEventStore,
        bus: AsyncEventBus,
        boundary: Optional[GovernanceBoundary] = None,
    ) -> None:
        self.store = store
        self.bus = bus
        self.boundary = boundary or GovernanceBoundary()

    async def observe(self, event: Event) -> str:
        try:
            await asyncio.to_thread(self.store.append, event)
        except StoreIntegrityError as exc:
            raise ObservatoryError(str(exc)) from exc

        await self.bus.publish(event)
        return event.id

    async def observe_many(self, events: List[Event]) -> List[str]:
        event_ids: List[str] = []

        for event in events:
            event_id = await self.observe(event)
            event_ids.append(event_id)

        return event_ids

    async def dashboard(self) -> Dict[str, Any]:
        overview = await self.overview()
        runtime = await self.runtime()
        governance = await self.governance()
        timeline = await self.timeline(limit=20)

        return {
            "overview": overview,
            "runtime": runtime,
            "governance": governance,
            "timeline": timeline,
        }

    async def overview(self) -> Dict[str, Any]:
        recent = await asyncio.to_thread(self.store.recent_events, 200, True)
        runtime = await self.runtime()
        governance = await self.governance()

        current_cycle = self._current_cycle(recent)
        evidence_count = await asyncio.to_thread(
            self.store.count_events_by_category,
            EventCategory.EVIDENCE,
        )

        return {
            "current_cycle": current_cycle,
            "status": self._overall_status(runtime, governance),
            "runtime_health": runtime["health"],
            "safe_mode": governance["safe_mode"],
            "evidence_count": evidence_count,
            "authorization_state": self._authorization_state(current_cycle, governance),
            "recent_event_count": len(recent),
        }

    async def runtime(self) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_category,
            EventCategory.RUNTIME,
            5000,
        )
        return projections.build_runtime_state(events)

    async def evolution(self, evolution_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(self.store.events_by_subject, evolution_id, 5000)

        if not events:
            raise NotFoundError(f"evolution {evolution_id} not found")

        return projections.build_evolution_state(evolution_id, events)

    async def evidence(self, evidence_id: str) -> Dict[str, Any]:
        subject_events = await asyncio.to_thread(
            self.store.events_by_subject,
            evidence_id,
            5000,
        )

        if subject_events:
            events = subject_events
        else:
            events = await asyncio.to_thread(
                self.store.events_by_category,
                EventCategory.EVIDENCE,
                10000,
            )

        record = projections.get_evidence(events, evidence_id)

        if record is None:
            raise NotFoundError(f"evidence {evidence_id} not found")

        return record

    async def requirement(self, requirement_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(self.store.events_by_subject, requirement_id, 5000)
        state = projections.build_requirement_state(requirement_id, events)

        if state is None:
            raise NotFoundError(f"requirement {requirement_id} not found")

        return state

    async def capability(self, capability_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(self.store.events_by_subject, capability_id, 5000)
        state = projections.build_capability_state(capability_id, events)

        if state is None:
            raise NotFoundError(f"capability {capability_id} not found")

        return state

    async def knowledge(self, subject_id: Optional[str] = None) -> Any:
        if subject_id is None:
            knowledge_events = await asyncio.to_thread(
                self.store.events_by_category,
                EventCategory.KNOWLEDGE,
                10000,
            )
            evidence_events = await asyncio.to_thread(
                self.store.events_by_category,
                EventCategory.EVIDENCE,
                10000,
            )
            return projections.build_knowledge_state(knowledge_events + evidence_events)

        events = await asyncio.to_thread(self.store.events_by_subject, subject_id, 5000)
        state = projections.get_knowledge(events, subject_id)

        if state is None:
            raise NotFoundError(f"knowledge subject {subject_id} not found")

        return state

    async def governance(self) -> Dict[str, Any]:
        events = await asyncio.to_thread(
            self.store.events_by_category,
            EventCategory.GOVERNANCE,
            10000,
        )
        return projections.build_governance_state(events)

    async def timeline(
        self,
        subject: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        if subject:
            events = await asyncio.to_thread(self.store.events_by_subject, subject, limit)

            if not events:
                raise NotFoundError(f"subject {subject} not found")

            events = list(reversed(events))
        else:
            events = await asyncio.to_thread(self.store.recent_events, limit, True)

        return [self._format_timeline_event(event) for event in events]

    async def health(self) -> Dict[str, Any]:
        runtime = await self.runtime()
        governance = await self.governance()

        event_count = await asyncio.to_thread(self.store.count_events)
        evidence_count = await asyncio.to_thread(
            self.store.count_events_by_category,
            EventCategory.EVIDENCE,
        )
        runtime_count = await asyncio.to_thread(
            self.store.count_events_by_category,
            EventCategory.RUNTIME,
        )
        governance_count = await asyncio.to_thread(
            self.store.count_events_by_category,
            EventCategory.GOVERNANCE,
        )

        return {
            "status": self._overall_status(runtime, governance),
            "runtime": runtime,
            "governance": governance,
            "store": {
                "event_count": event_count,
                "evidence_event_count": evidence_count,
                "runtime_event_count": runtime_count,
                "governance_event_count": governance_count,
            },
        }

    async def trace(self, subject_id: str) -> List[Dict[str, Any]]:
        events = await asyncio.to_thread(self.store.events_by_subject, subject_id, 10000)

        if not events:
            raise NotFoundError(f"subject {subject_id} not found")

        return [event.model_dump(mode="json") for event in events]

    async def explain(self, subject_id: str) -> Dict[str, Any]:
        events = await asyncio.to_thread(self.store.events_by_subject, subject_id, 10000)

        if not events:
            raise NotFoundError(f"subject {subject_id} not found")

        if any(event.category == EventCategory.EVOLUTION for event in events):
            state = projections.build_evolution_state(subject_id, events)
            return {
                "subject_id": subject_id,
                "explanation_type": "evolution",
                "decision": state["decision"],
                "status": state["status"],
                "epistemic_state": state["epistemic_state"],
                "capability_check": state["capability_check"],
                "authorization": state["authorization"],
                "unknowns": state["unknowns"],
                "contradictions": state["contradictions"],
                "pipeline": state["pipeline"],
                "trace": [event.id for event in events],
            }

        if any(event.category == EventCategory.EVIDENCE for event in events):
            record = projections.get_evidence(events, subject_id)

            if record is not None:
                return {
                    "subject_id": subject_id,
                    "explanation_type": "evidence",
                    "claim": record["claim"],
                    "epistemic_status": record["epistemic_status"],
                    "result": record["result"],
                    "scope": record["scope"],
                    "not_proven": record["not_proven"],
                    "provenance": record["provenance"],
                    "trace": [event.id for event in events],
                }

        return {
            "subject_id": subject_id,
            "explanation_type": "generic",
            "epistemic_state": projections.count_epistemic(events),
            "latest_event_type": events[-1].type,
            "latest_timestamp": events[-1].timestamp,
            "trace": [event.id for event in events],
        }

    async def request_command(
        self,
        command: CommandRequest,
        actor: Actor,
    ) -> Dict[str, Any]:
        action = command.action

        if action not in COMMAND_ACTIONS:
            raise AuthorizationError("unsupported_action")

        governance_state = await self.governance()
        authority = governance_state["current_authority"]

        try:
            self.boundary.authorize(action, actor, authority)
        except AuthorizationError as exc:
            await self._audit_rejection(action, command.params, actor, str(exc))
            raise

        request_id = self._generate_request_id(action, command.params)
        target_id = str(command.params.get("target_id") or request_id)

        event = new_governance_event(
            source="observatory_gateway",
            type="command_requested",
            subject_id=target_id,
            payload={
                "request_id": request_id,
                "action": action,
                "params": self._redact(command.params),
                "actor_id": actor.id,
            },
        )

        await self.observe(event)

        return {
            "request_id": request_id,
            "status": "pending",
        }

    async def _audit_rejection(
        self,
        action: str,
        params: Dict[str, Any],
        actor: Actor,
        reason: str,
    ) -> None:
        try:
            event = new_governance_event(
                source="observatory_gateway",
                type="command_rejected",
                subject_id=str(params.get("target_id") or "GOVERNANCE"),
                reason=reason,
                severity="warning",
                payload={
                    "action": action,
                    "params": self._redact(params),
                    "actor_id": actor.id,
                },
            )
            await self.observe(event)
        except Exception:
            # Audit failure must not mask the original authorization failure.
            pass

    def _current_cycle(self, recent_events_desc: List[Event]) -> Optional[Dict[str, Any]]:
        for event in recent_events_desc:
            if event.category == EventCategory.EVOLUTION:
                return {
                    "evolution_id": event.subject_id,
                    "latest_event_type": event.type,
                    "updated_at": event.timestamp,
                }

        return None

    def _overall_status(
        self,
        runtime: Dict[str, Any],
        governance: Dict[str, Any],
    ) -> str:
        if runtime["health"] == "degraded":
            return "degraded"

        if governance["safe_mode"] == "enabled":
            return "safe_mode"

        if runtime["health"] == "green":
            return "operational"

        return "unknown"

    def _authorization_state(
        self,
        current_cycle: Optional[Dict[str, Any]],
        governance: Dict[str, Any],
    ) -> str:
        if current_cycle is None:
            return "not_applicable"

        if governance["current_authority"].get("implementation") == "none":
            return "required"

        return "granted"

    def _format_timeline_event(self, event: Event) -> Dict[str, Any]:
        summary = event.payload.get("summary")

        if summary is None:
            summary = f"{event.type}: {event.subject_id}"

        return {
            "event_id": event.id,
            "timestamp": event.timestamp,
            "category": event.category.value,
            "type": event.type,
            "subject_id": event.subject_id,
            "epistemic_status": event.epistemic_status.value,
            "severity": event.severity.value,
            "summary": summary,
        }

    def _generate_request_id(self, action: str, params: Dict[str, Any]) -> str:
        basis = canonical_json(
            {
                "action": action,
                "params": self._redact(params),
                "timestamp": utc_now().isoformat(),
            }
        )
        digest = sha256_hex(basis)
        return f"REQ-{digest[:20]}"

    def _redact(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if self._secret_key(key) else self._redact(item)
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [self._redact(item) for item in value]

        return value

    def _secret_key(self, key: Any) -> bool:
        normalized = str(key).lower()
        return any(marker in normalized for marker in SECRET_KEY_MARKERS)
```

---

# 10. API dependencies

**`observatory/backend/api/deps.py`**

```python
from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, Request

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
    actor: Actor = None,
    x_observatory_token: Optional[str] = Header(default=None),
) -> Actor:
    settings = get_settings()

    if settings.api_token and x_observatory_token != settings.api_token:
        raise HTTPException(status_code=401, detail="invalid observatory token")

    if actor is None:
        raise HTTPException(status_code=401, detail="actor required")

    if actor.role not in {"operator", "architect", "admin", "system"}:
        raise HTTPException(status_code=403, detail="writer role required")

    return actor


def require_operator(
    actor: Actor = None,
    x_observatory_token: Optional[str] = Header(default=None),
) -> Actor:
    settings = get_settings()

    if settings.api_token and x_observatory_token != settings.api_token:
        raise HTTPException(status_code=401, detail="invalid observatory token")

    if actor is None:
        raise HTTPException(status_code=401, detail="actor required")

    clearance = actor.clearance or actor.role

    if clearance not in {"operator", "architect", "admin"}:
        raise HTTPException(status_code=403, detail="operator clearance required")

    return actor
```

---

# 11. API routes

**`observatory/backend/api/routes.py`**

```python
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from ..domain import Actor, CommandRequest, EventInput, event_from_input
from ..gateway import ObservatoryGateway
from .deps import get_actor, get_gateway, require_operator, require_writer

router = APIRouter(prefix="/observatory", tags=["observatory"])


@router.get("/dashboard")
async def dashboard(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.dashboard()


@router.get("/overview")
async def overview(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.overview()


@router.get("/runtime")
async def runtime(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.runtime()


@router.get("/governance")
async def governance(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.governance()


@router.get("/health")
async def health(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.health()


@router.get("/timeline")
async def timeline(
    subject: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.timeline(subject=subject, limit=limit)


@router.get("/evolution/{evolution_id}")
async def evolution(
    evolution_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.evolution(evolution_id)


@router.get("/evidence/{evidence_id}")
async def evidence(
    evidence_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.evidence(evidence_id)


@router.get("/requirement/{requirement_id}")
async def requirement(
    requirement_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.requirement(requirement_id)


@router.get("/capability/{capability_id}")
async def capability(
    capability_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.capability(capability_id)


@router.get("/knowledge")
async def knowledge_all(gateway: ObservatoryGateway = Depends(get_gateway)):
    return await gateway.knowledge(None)


@router.get("/knowledge/{subject_id}")
async def knowledge_subject(
    subject_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.knowledge(subject_id)


@router.get("/trace/{subject_id}")
async def trace(
    subject_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.trace(subject_id)


@router.get("/explain/{subject_id}")
async def explain(
    subject_id: str,
    gateway: ObservatoryGateway = Depends(get_gateway),
):
    return await gateway.explain(subject_id)


@router.post("/events")
async def ingest_event(
    event_input: EventInput,
    gateway: ObservatoryGateway = Depends(get_gateway),
    actor: Actor = Depends(require_writer),
):
    event = event_from_input(event_input)
    event_id = await gateway.observe(event)

    return {
        "status": "accepted",
        "event_id": event_id,
        "actor_id": actor.id,
    }


@router.post("/commands")
async def request_command(
    command: CommandRequest,
    gateway: ObservatoryGateway = Depends(get_gateway),
    actor: Actor = Depends(require_operator),
):
    return await gateway.request_command(command, actor)


@router.get("/stream")
async def stream(gateway: ObservatoryGateway = Depends(get_gateway)):
    queue = gateway.bus.subscribe()

    async def event_stream():
        try:
            while True:
                event = await queue.get()
                yield f"data: {event.model_dump_json()}\n\n"
        finally:
            gateway.bus.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

---

# 12. Application entrypoint

**`observatory/backend/main.py`**

```python
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import router
from .bus import AsyncEventBus
from .config import get_settings
from .governance import AuthorizationError
from .gateway import NotFoundError, ObservatoryError, ObservatoryGateway
from .store import SqliteEventStore, StoreIntegrityError


def create_app() -> FastAPI:
    settings = get_settings()

    store = SqliteEventStore(settings.db_path)
    store.init()

    bus = AsyncEventBus()
    gateway = ObservatoryGateway(store=store, bus=bus)

    app = FastAPI(
        title="Tiannara Observatory Backend",
        description=(
            "Python-native Observatory backend for Tiannara. "
            "This service provides canonical event ingestion, epistemic projections, "
            "traceability, and governed command requests. It does not execute "
            "evolution, deployment, or production mutation."
        ),
        version="0.1.0",
    )

    app.state.gateway = gateway

    app.include_router(router)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/", tags=["meta"])
    async def root():
        return {
            "service": "Tiannara Observatory Backend",
            "status": "ok",
            "endpoints": "/observatory/*",
        }

    @app.get("/healthz", tags=["meta"])
    async def healthz():
        return {"status": "ok"}

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found",
                "detail": str(exc),
            },
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=403,
            content={
                "error": "authorization_failed",
                "detail": str(exc),
            },
        )

    @app.exception_handler(StoreIntegrityError)
    async def store_integrity_handler(request: Request, exc: StoreIntegrityError):
        return JSONResponse(
            status_code=409,
            content={
                "error": "store_integrity_error",
                "detail": str(exc),
            },
        )

    @app.exception_handler(ObservatoryError)
    async def observatory_error_handler(request: Request, exc: ObservatoryError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "observatory_error",
                "detail": str(exc),
            },
        )

    return app


app = create_app()
```

---

# 13. Empty package markers

Create empty files:

```text
observatory/__init__.py
observatory/backend/__init__.py
observatory/backend/api/__init__.py
```

---

# 14. Run the backend

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the server:

```bash
uvicorn observatory.backend.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive docs:

```text
http://127.0.0.1:8000/docs
```

---

# 15. Example event ingestion

```bash
curl -X POST http://127.0.0.1:8000/observatory/events \
  -H "Content-Type: application/json" \
  -H "X-Actor-Id: runtime-adapter" \
  -H "X-Actor-Role: system" \
  -d '{
    "source": "tiannara.runtime",
    "category": "runtime",
    "type": "process_started",
    "subject_id": "Tiannara.Runtime.AgencyLoop",
    "payload": {
      "process": "AgencyLoop",
      "summary": "AgencyLoop started"
    }
  }'
```

---

# 16. Example governed command request

```bash
curl -X POST http://127.0.0.1:8000/observatory/commands \
  -H "Content-Type: application/json" \
  -H "X-Actor-Id: human-operator" \
  -H "X-Actor-Role: operator" \
  -H "X-Actor-Clearance: operator" \
  -d '{
    "action": "request_evolution_definition",
    "params": {
      "target_id": "EV-002"
    }
  }'
```

Expected behavior:

```text
request accepted → command_requested event emitted
```

If authority is absent:

```text
403 authorization_failed
command_rejected event emitted
```

---

# 17. What this backend establishes

This Python backend now provides the core Observatory contract:

```text
observe/ingest events
    ↓
persist canonical events
    ↓
project read models
    ↓
serve API read views
    ↓
stream live events
    ↓
accept governed command requests
    ↓
preserve authorization boundary
```

It does **not**:

```text
execute evolution
execute deployment
mutate ISR
mutate Tiannara runtime
authorize production
bypass governance
fabricate unknowns
```

---

# 18. Next backend step

The next backend layer should be the **Tiannara runtime adapter**.

That adapter will connect this Observatory backend to the real Python Tiannara system by translating real runtime, evolution, evidence, and governance occurrences into canonical Observatory events.

Recommended adapter boundary:

```text
Tiannara runtime / evolution engine
        ↓
ObservatoryAdapter
        ↓
POST /observatory/events
        ↓
Observatory backend
        ↓
UI read models / live stream
```

That keeps the Observatory as a first-class Python subsystem without introducing a second runtime.