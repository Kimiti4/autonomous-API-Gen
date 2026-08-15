"""
ISR Serializer.

Converts an ISR object model to canonical JSON for persistence,
transmission, and caching.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from constitutional_architecture.isr.model.isr import ISR


class ISRSerializer:
    """
    Serializes ISR to canonical JSON.

    Canonical JSON guarantees:
    - Deterministic key ordering (sorted)
    - No whitespace variance
    - Consistent enum representation (string values)
    - Consistent datetime format (ISO 8601 UTC)
    """

    @staticmethod
    def to_json(isr: ISR, indent: int | None = 2) -> str:
        data = ISRSerializer._to_dict(isr)
        return json.dumps(data, indent=indent, sort_keys=True, default=ISRSerializer._json_default)

    @staticmethod
    def to_canonical_json(isr: ISR) -> str:
        data = ISRSerializer._to_dict(isr)
        return json.dumps(data, sort_keys=True, separators=(",", ":"), default=ISRSerializer._json_default)

    @staticmethod
    def to_dict(isr: ISR) -> dict[str, Any]:
        return ISRSerializer._to_dict(isr)

    @staticmethod
    def _to_dict(obj: Any) -> Any:
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (list, tuple)):
            return [ISRSerializer._to_dict(item) for item in obj]
        if isinstance(obj, frozenset):
            return sorted(ISRSerializer._to_dict(item) for item in obj)
        if isinstance(obj, set):
            return sorted(ISRSerializer._to_dict(item) for item in obj)
        if isinstance(obj, dict):
            return {
                ISRSerializer._to_dict(k): ISRSerializer._to_dict(v)
                for k, v in sorted(obj.items(), key=lambda x: str(x[0]))
            }
        if is_dataclass(obj) and not isinstance(obj, type):
            return ISRSerializer._to_dict(asdict(obj))
        if hasattr(obj, "__dict__"):
            return {
                k: ISRSerializer._to_dict(v)
                for k, v in sorted(vars(obj).items())
                if not k.startswith("_")
            }
        return str(obj)

    @staticmethod
    def _json_default(obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, (set, frozenset)):
            return sorted(obj)
        if is_dataclass(obj):
            return asdict(obj)
        return str(obj)
