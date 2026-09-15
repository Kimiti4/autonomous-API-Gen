"""Secret redaction for adapter payloads (applied before transport).

Safe direction only: secret-shaped keys become [REDACTED], long strings
truncate with a visible marker, depth overflow is marked. Tuples normalize
to lists (documented; JSON has no tuple type).
"""
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
        return {key: "[REDACTED]" if is_secret_key(key)
                else redact(item, depth - 1)
                for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item, depth - 1) for item in value]
    if isinstance(value, tuple):
        return [redact(item, depth - 1) for item in value]
    if isinstance(value, str):
        return truncate_string(value)
    return value
