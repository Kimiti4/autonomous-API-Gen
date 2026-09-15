"""VS-D25 — PriorityQueryPolicy: the D24-selected query-policy-separation seam.

Task persistence stays in the task domain (via TaskV3Repository); this
boundary owns priority validation, legacy defaulting, and filter-semantics
decisions. It is authorization-adjacent but never authorization: callers
must enforce membership BEFORE delegating here. Mirrors the precedent set
by AuthorizationPolicy (explicit boundary, no inline service logic).
"""

from __future__ import annotations

from typing import Any, Callable

from vertical_slice.app.service import ValidationError
from vertical_slice.app_v3.models import (
    LEGACY_DEFAULT_PRIORITY,
    PRIORITY_VALUES,
    TaskV3,
)


class PriorityQueryPolicy:
    """Single place where priority semantics are decided."""

    def __init__(self, allowed: tuple[str, ...] = PRIORITY_VALUES,
                 legacy_default: str = LEGACY_DEFAULT_PRIORITY) -> None:
        if set(allowed) != set(PRIORITY_VALUES):
            raise ValidationError("priority domain is closed to LOW/MEDIUM/HIGH")
        self._allowed = allowed
        self._legacy_default = legacy_default

    @property
    def allowed_values(self) -> tuple[str, ...]:
        return self._allowed

    def validate_priority(self, value: object) -> str:
        """Fail-closed validation: no coercion of arbitrary values."""
        if not isinstance(value, str) or value not in self._allowed:
            raise ValidationError(
                "priority must be one of LOW, MEDIUM, HIGH")
        return value

    def default_for_missing(self) -> str:
        return self._legacy_default

    def apply_legacy_default(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Deterministic legacy migration: records lacking priority read as
        MEDIUM. Pure function; persistence of the default happens on the
        next task write, never as a side effect here."""
        if not raw.get("priority"):
            return {**raw, "priority": self._legacy_default}
        self.validate_priority(raw["priority"])
        return raw

    def build_filter(self, priority: object) -> Callable[[TaskV3], bool]:
        """Filter-semantics decision: None means no predicate; any other
        value must validate (invalid filter values fail closed, 422)."""
        if priority is None:
            return lambda _task: True
        wanted = self.validate_priority(priority)
        return lambda task: task.priority == wanted
