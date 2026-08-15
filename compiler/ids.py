"""
Deterministic identifier and hashing utilities for the compiler.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


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