"""Authenticated delivery of governed-maintenance evidence to Observatory.

This bridge publishes an evidence event only. It does not mutate repositories or
authorize deployment. The Observatory remains responsible for durable event storage
and stream fan-out.
"""
from __future__ import annotations

import json
from hashlib import sha256
import math
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .governed_maintenance_execution import record_verified_maintenance


class ObservatoryDeliveryError(RuntimeError):
    """Raised when the Observatory does not confirm event ingestion."""


def deliver_maintenance_event(
    record: Any,
    event: Any,
    *,
    base_url: str,
    token: str,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 5.0,
) -> str:
    """POST a digest-linked maintenance event and return the stored event ID.

    Configuration is explicit so callers cannot accidentally send events to an
    implicit/default endpoint. A successful HTTP response alone is insufficient:
    the Observatory must return its normal accepted/event_id acknowledgement.
    """
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("observatory-base-url-required")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("observatory-token-required")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("invalid-observatory-timeout")
    parsed_url = urlsplit(base_url.strip())
    local_http_hosts = {"localhost", "127.0.0.1", "::1"}
    if (
        not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
        or not (
            parsed_url.scheme == "https"
            or (parsed_url.scheme == "http" and parsed_url.hostname.lower() in local_http_hosts)
        )
    ):
        raise ValueError("observatory-base-url-invalid")
    if getattr(event, "status", None) != "verified":
        raise ValueError("maintenance-event-not-verified")
    if not getattr(event, "digest", None) or len(event.digest) != 64:
        raise ValueError("maintenance-event-digest-invalid")
    if getattr(event, "repair_report_digest", None) is None:
        raise ValueError("maintenance-event-report-digest-missing")
    if (
        getattr(event, "observation_digest", None) != record.observation_digest
        or getattr(event, "obligation_id", None) != record.obligation_id
        or getattr(event, "patch_digest", None) != record.patch_digest
        or tuple(getattr(event, "evidence", ())) != tuple(record.verification_evidence)
    ):
        raise ValueError("maintenance-event-record-linkage-mismatch")
    digest_payload = {
        "event_type": event.event_type,
        "status": event.status,
        "observation_digest": event.observation_digest,
        "obligation_id": event.obligation_id,
        "patch_digest": event.patch_digest,
        "repair_report_digest": event.repair_report_digest,
        "evidence": list(event.evidence),
    }
    expected_digest = sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if event.digest != expected_digest:
        raise ValueError("maintenance-event-digest-mismatch")

    payload = {
        "event_type": "governed_maintenance_recorded",
        "status": event.status,
        "observation_digest": record.observation_digest,
        "obligation_id": record.obligation_id,
        "patch_digest": record.patch_digest,
        "repair_report_digest": event.repair_report_digest,
        "maintenance_event_digest": event.digest,
        "authorization_ref": record.authorization_ref,
        "production_write_requested": bool(record.production_write_requested),
        "verification_evidence": list(record.verification_evidence),
    }
    body = {
        "id": f"maintenance-{event.digest}",
        "source": "esap.governed-maintenance",
        "category": "evidence",
        "type": "governed_maintenance_recorded",
        "subject_id": record.obligation_id,
        "payload": payload,
        "epistemic_status": "observed",
        "severity": "info",
        "evidence_refs": [
            record.observation_digest,
            record.patch_digest,
            event.repair_report_digest,
            event.digest,
            *record.verification_evidence,
        ],
        "provenance": {
            "producer": "autonomous-api-gen",
            "contract": "governed-maintenance-v1",
        },
    }
    url = base_url.strip().rstrip("/") + "/observatory/events"
    request = Request(
        url,
        data=json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Observatory-Token": token,
            "Idempotency-Key": "maintenance-" + event.digest,
            "X-Actor-Id": "esap-maintenance-bridge",
            "X-Actor-Role": "system",
            "X-Actor-Clearance": "system",
        },
        method="POST",
    )
    try:
        response = opener(request, timeout=timeout)
        try:
            status_code = getattr(response, "status", None)
            raw = response.read()
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
    except (URLError, TimeoutError, OSError) as exc:
        raise ObservatoryDeliveryError("observatory-event-delivery-failed") from exc

    if status_code is None or not 200 <= status_code < 300:
        raise ObservatoryDeliveryError("observatory-event-ingestion-rejected")
    try:
        acknowledgement = json.loads(raw.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ObservatoryDeliveryError("observatory-acknowledgement-invalid") from exc
    if not isinstance(acknowledgement, dict):
        raise ObservatoryDeliveryError("observatory-acknowledgement-invalid")
    event_id = acknowledgement.get("event_id")
    if acknowledgement.get("status") != "accepted" or not isinstance(event_id, str) or not event_id.strip():
        raise ObservatoryDeliveryError("observatory-acknowledgement-invalid")
    return event_id



def record_and_deliver_verified_maintenance(
    observation: Any,
    admission: Any,
    *,
    obligation_id: str,
    authorization_ref: str,
    repair_report: Any,
    base_url: str,
    token: str,
    production_write_requested: bool = False,
    opener: Callable[..., Any] = urlopen,
    timeout: float = 5.0,
) -> tuple[Any, Any, str]:
    """Validate, construct, and deliver a maintenance event as one caller flow.

    The remote acknowledgement is returned only after Observatory accepts the
    event. This function does not persist a local outbox; callers must retain
    evidence and handle delivery failures without treating them as successful.
    """
    record, event = record_verified_maintenance(
        observation,
        admission,
        obligation_id=obligation_id,
        authorization_ref=authorization_ref,
        repair_report=repair_report,
        production_write_requested=production_write_requested,
    )
    event_id = deliver_maintenance_event(
        record, event, base_url=base_url, token=token,
        opener=opener, timeout=timeout,
    )
    return record, event, event_id
