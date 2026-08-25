"""Identity + canonical serialization helpers. Framework-agnostic.

Constitutional notes:
- uuid7() implements RFC 9562 UUIDv7 (time-sortable, globally unique).
- canonical_json() exists SOLELY for content hashing (sorted keys, no
  whitespace). Do not use it for wire serialization.
- No FastAPI / DB / engine imports may ever appear in this module.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from typing import Any


def uuid7() -> uuid.UUID:
    """Time-sortable UUIDv7 (RFC 9562). Dependency-free implementation.

    Layout: 48-bit unix-ms | 4-bit version(0b0111) | 12-bit rand_a
            | 2-bit variant(0b10) | 62-bit rand_b
    """
    ts_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF
    value = (
        (ts_ms << 80)
        | (0x7 << 76)          # version 7
        | (rand_a << 64)
        | (0b10 << 62)         # RFC 4122 variant
        | rand_b
    )
    return uuid.UUID(int=value)


def canonical_json(payload: Any) -> str:
    """Deterministic JSON used for content hashing.

    Sorted keys, no whitespace, ASCII-escaped, stable default for
    non-serializable types. Do NOT use this for wire serialization
    (use model_dump_json for that); it exists solely for hashing.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def content_hash(payload: Any) -> str:
    """SHA-256 of the canonical JSON of `payload`."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()