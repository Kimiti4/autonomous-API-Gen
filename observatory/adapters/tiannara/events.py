"""Adapter-side canonical event construction (plain dicts).

Mirrors the backend domain vocabulary (categories, severities, epistemic
states) without importing the backend: the adapter must remain usable
from runtimes that do not bundle the Observatory package. Canonical JSON
uses the repo standard (sorted keys, compact separators, UTF-8 native).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

VALID_CATEGORIES = {"runtime", "evidence", "evolution", "governance",
                    "knowledge"}
VALID_SEVERITIES = {"debug", "info", "warning", "error", "fatal"}
VALID_EPISTEMIC_STATUSES = {"observed", "inferred", "unknown",
                            "contradiction"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Any) -> str:
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
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def generate_event_id(*, source: str, category: str, type: str,
                      subject_id: str, payload: Dict[str, Any],
                      timestamp: datetime) -> str:
    basis = canonical_json({
        "source": source, "category": category, "type": type,
        "subject_id": subject_id, "payload": payload,
        "timestamp": timestamp.isoformat()})
    return f"evt-{category}-{sha256_hex(basis)[:24]}"


def build_event(*, source: str, category: str, type: str, subject_id: str,
                payload: Optional[Dict[str, Any]] = None,
                severity: str = "info",
                epistemic_status: str = "observed",
                correlation_id: Optional[str] = None,
                causation_id: Optional[str] = None,
                evidence_refs: Optional[List[str]] = None,
                provenance: Optional[Dict[str, Any]] = None,
                timestamp: Optional[datetime] = None,
                event_id: Optional[str] = None) -> Dict[str, Any]:
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
        source=source, category=category, type=type, subject_id=subject_id,
        payload=resolved_payload, timestamp=resolved_timestamp)
    return {
        "id": resolved_id, "timestamp": resolved_timestamp.isoformat(),
        "source": source, "category": category, "type": type,
        "subject_id": subject_id, "correlation_id": correlation_id,
        "causation_id": causation_id, "payload": resolved_payload,
        "epistemic_status": epistemic_status, "authorization": None,
        "evidence_refs": list(evidence_refs or []),
        "provenance": dict(provenance or {}), "severity": severity}
