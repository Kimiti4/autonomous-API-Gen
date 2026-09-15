"""Canonical event envelope, epistemic typing, and constructors.

Epistemic rule enforced here: missing data is never fabricated.
A missing result is not success; an unmeasured metric is not zero.
"""
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
    # Repo canonical form: sorted keys, compact separators, UTF-8 native.
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


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


class BatchEventInput(BaseModel):
    events: List[EventInput] = Field(default_factory=list)


class BatchIngestionResponse(BaseModel):
    status: str
    accepted: int
    inserted: int
    duplicates: int
    event_ids: List[str]


class Actor(BaseModel):
    id: str
    role: str
    clearance: Optional[str] = None


class CommandRequest(BaseModel):
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)


def event_hash(event: Event) -> str:
    return sha256_hex(canonical_json(event.model_dump(mode="json")))


def generate_event_id(*, category: EventCategory, source: str, type: str,
                      subject_id: str, payload: Dict[str, Any],
                      timestamp: datetime) -> str:
    basis = canonical_json({
        "category": category.value, "source": source, "type": type,
        "subject_id": subject_id, "payload": payload,
        "timestamp": timestamp.isoformat()})
    return f"evt-{category.value}-{sha256_hex(basis)[:24]}"


def new_event(*, category: EventCategory, source: str, type: str,
              subject_id: str, payload: Optional[Dict[str, Any]] = None,
              epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED,
              severity: Severity = Severity.INFO,
              evidence_refs: Optional[List[str]] = None,
              provenance: Optional[Dict[str, Any]] = None,
              timestamp: Optional[datetime] = None,
              id: Optional[str] = None,
              correlation_id: Optional[str] = None,
              causation_id: Optional[str] = None,
              authorization: Optional[str] = None) -> Event:
    if not source:
        raise ValueError("event source is required")
    if not type:
        raise ValueError("event type is required")
    if not subject_id:
        raise ValueError("event subject_id is required")
    resolved_timestamp = parse_timestamp(timestamp)
    resolved_payload = dict(payload or {})
    resolved_id = id or generate_event_id(
        category=category, source=source, type=type, subject_id=subject_id,
        payload=resolved_payload, timestamp=resolved_timestamp)
    return Event(
        id=resolved_id, timestamp=resolved_timestamp, source=source,
        category=category, type=type, subject_id=subject_id,
        correlation_id=correlation_id, causation_id=causation_id,
        payload=resolved_payload, epistemic_status=epistemic_status,
        authorization=authorization, evidence_refs=list(evidence_refs or []),
        provenance=dict(provenance or {}),
        severity=severity)


def new_runtime_event(**kwargs: Any) -> Event:
    return new_event(category=EventCategory.RUNTIME, **kwargs)


def new_evolution_event(**kwargs: Any) -> Event:
    return new_event(category=EventCategory.EVOLUTION, **kwargs)


def new_knowledge_event(**kwargs: Any) -> Event:
    return new_event(category=EventCategory.KNOWLEDGE, **kwargs)


def new_evidence_event(*, source: str, subject_id: str, claim: str,
                       result: Any, scope: Optional[List[str]] = None,
                       not_proven: Optional[List[str]] = None,
                       epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED,
                       type: str = "evidence_recorded",
                       payload: Optional[Dict[str, Any]] = None,
                       **kwargs: Any) -> Event:
    if not claim:
        raise ValueError("evidence claim is required")
    if result is None:
        raise ValueError("evidence result is required")
    resolved_payload = dict(payload or {})
    resolved_payload.update({"claim": claim, "result": result,
                             "scope": list(scope or []),
                             "not_proven": list(not_proven or [])})
    return new_event(category=EventCategory.EVIDENCE, source=source,
                     type=type, subject_id=subject_id,
                     payload=resolved_payload,
                     epistemic_status=epistemic_status, **kwargs)


def new_governance_event(*, source: str, type: str,
                         subject_id: str = "GOVERNANCE",
                         reason: Optional[str] = None,
                         payload: Optional[Dict[str, Any]] = None,
                         **kwargs: Any) -> Event:
    resolved_payload = dict(payload or {})
    if type == "command_rejected" and not reason:
        raise ValueError("command_rejected events require a reason")
    if reason is not None:
        resolved_payload["reason"] = reason
    return new_event(category=EventCategory.GOVERNANCE, source=source,
                     type=type, subject_id=subject_id,
                     payload=resolved_payload, **kwargs)


def event_from_input(event_input: EventInput) -> Event:
    return new_event(
        category=event_input.category, source=event_input.source,
        type=event_input.type, subject_id=event_input.subject_id,
        payload=event_input.payload,
        epistemic_status=event_input.epistemic_status,
        severity=event_input.severity,
        evidence_refs=event_input.evidence_refs,
        provenance=event_input.provenance, timestamp=event_input.timestamp,
        id=event_input.id, correlation_id=event_input.correlation_id,
        causation_id=event_input.causation_id,
        authorization=event_input.authorization)
