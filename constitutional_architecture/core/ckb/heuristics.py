"""
Phase 18 — Constitutional Knowledge Base (CKB) Heuristic Store.

A real, bounded backend for the CKBUpdater's `adjust_heuristic` contract.

Heuristic adjustments are recorded as per-(pattern, quality-attribute)
deltas, accumulated at the learning rate and saturated to prevent
catastrophic drift. This is the mutation surface the Learning Kernel may
touch: architectural heuristics only, never implementation code.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from constitutional_architecture.core.models.intent import QualityAttribute

MAX_ABSOLUTE_DELTA = 0.5


def _key(pattern: str, attr: Any) -> str:
    if isinstance(attr, Enum):
        attr = attr.value
    return f"{pattern}::{attr}"


class HeuristicAdjustmentStore:
    """Append-only, bounded record of CKB heuristic adjustments."""

    def __init__(self) -> None:
        self._deltas: Dict[str, float] = {}
        self._history: list[Dict[str, Any]] = []

    def adjust_heuristic(self, pattern: str, attr: Any,
                         direction: int = -1, rate: float = 0.05) -> None:
        """Shift the heuristic for (pattern, attr) by `rate` in `direction`."""
        key = _key(pattern, attr)
        delta = direction * rate
        self._deltas[key] = max(
            -MAX_ABSOLUTE_DELTA,
            min(MAX_ABSOLUTE_DELTA, self._deltas.get(key, 0.0) + delta),
        )
        self._history.append({
            "pattern": pattern,
            "attribute": attr.value if isinstance(attr, Enum) else str(attr),
            "direction": direction,
            "rate": rate,
            "accumulated": self._deltas[key],
        })

    def get_delta(self, pattern: str, attr: Any) -> float:
        return self._deltas.get(_key(pattern, attr), 0.0)

    def adjusted_attributes(self) -> Dict[str, float]:
        return dict(self._deltas)

    @property
    def history(self) -> list[Dict[str, Any]]:
        return list(self._history)
