"""
Deterministic identity and hashing utilities.

Knowledge Graph entities and relations must be idempotently ingestable.
IDs are therefore derived from canonicalized content hashes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    """
    Produce a canonical JSON representation.

    This is used for deterministic hashing.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def sha256_hex(value: str) -> str:
    """Return a SHA-256 hex digest for a UTF-8 string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def deterministic_id(prefix: str, payload: dict[str, Any]) -> str:
    """
    Build a deterministic prefixed identifier from canonical payload content.

    Example:
        deterministic_id("entity", {"name": "BillingService"})
    """
    return f"{prefix}_{sha256_hex(canonical_json(payload))}"
