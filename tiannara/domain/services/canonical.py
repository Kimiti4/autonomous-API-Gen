"""Canonical serialization utilities.

Determinism is a constitutional requirement: identical semantic content
must always produce identical hashes, across processes and platforms. This
is what makes evidence chains, ISR lineage, and certification runs
reproducible and auditable.

These helpers are shared by the ISR envelope, the typed SystemModel payload,
the RequirementGraph, and (in later phases) the synthesizer's provenance
records.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def to_jsonable(value: Any) -> Any:
    """Convert a value (or pydantic model) into plain JSON-able types."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def canonical_json(value: Any) -> str:
    """Serialize any JSON-able value or pydantic model deterministically.

    Rules:
      * dict keys sorted recursively (so insertion order never matters);
      * compact separators, ASCII-escaped (stable across platforms);
      * list order preserved (lists carry semantic order).
    """
    obj = to_jsonable(value)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: Any) -> str:
    """SHA-256 over the canonical JSON form of a value or model."""
    return sha256_hex(canonical_json(value))
