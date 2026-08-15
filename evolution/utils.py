"""
Utilities for the Self-Evolution Engine.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    """Return timezone-aware UTC current time."""
    return datetime.now(timezone.utc)


def canonical_json(payload: Any) -> str:
    """Produce canonical JSON for deterministic hashing."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_hex(value: str) -> str:
    """Return SHA-256 hex digest for a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def deterministic_id(prefix: str, payload: dict[str, Any]) -> str:
    """Build a deterministic prefixed identifier."""
    return f"{prefix}_{sha256_hex(canonical_json(payload))}"


def deep_copy(payload: Any) -> Any:
    """Deep copy a payload."""
    return copy.deepcopy(payload)


def iter_services(isr: dict[str, Any]):
    """Yield service definitions from an ISR payload."""

    domains = isr.get("domains", []) or []

    for domain in domains:
        if not isinstance(domain, dict):
            continue

        services = domain.get("services", []) or []

        for service in services:
            if isinstance(service, dict):
                yield service
            elif isinstance(service, str):
                yield {"name": service}

    services = isr.get("services", []) or []

    for service in services:
        if isinstance(service, dict):
            yield service
        elif isinstance(service, str):
            yield {"name": service}


def iter_data_models(isr: dict[str, Any]):
    """Yield data model definitions from an ISR payload."""

    for model in isr.get("data_models", []) or []:
        yield model

    for service in iter_services(isr):
        for model in service.get("data_models", []) or []:
            yield model


def collect_api_names(isr: dict[str, Any]) -> set[str]:
    """Collect normalized API names from ISR."""

    api_names: set[str] = set()

    for service in iter_services(isr):
        apis = service.get("apis", []) or []

        for api in apis:
            if isinstance(api, str):
                api_names.add(api)
            elif isinstance(api, dict):
                name = api.get("name")

                if name:
                    api_names.add(str(name))

    return api_names
