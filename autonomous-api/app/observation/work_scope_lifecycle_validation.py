"""Strict validation of ESAP work-scope Observatory lifecycle ordering."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class LifecycleIssue:
    code: str
    detail: str


@dataclass(frozen=True)
class LifecycleValidation:
    valid: bool
    issues: tuple[LifecycleIssue, ...]


def validate_work_scope_lifecycle(events: Iterable[object]) -> LifecycleValidation:
    """Validate event ordering/identity without inventing missing outcomes."""
    scope_seen = False
    scope_key = None
    authorized: dict[tuple[str, str, str], str] = {}
    executed: dict[tuple[str, str, str], str] = {}
    issues: list[LifecycleIssue] = []

    ordered = sorted(
        tuple(events),
        key=lambda e: getattr(e, "sequence", -1),
    )
    for event in ordered:
        typ = getattr(event, "eventType", None)
        payload = getattr(event, "payload", None)
        if typ == "scope.declared":
            key = (payload.projectIntent, payload.projectKind, payload.generationScope)
            if scope_seen:
                issues.append(LifecycleIssue("MULTIPLE_SCOPE_DECLARATIONS", "scope declared more than once"))
            else:
                scope_seen = True
                scope_key = key
        elif typ == "mutation.authorization":
            if not scope_seen:
                issues.append(LifecycleIssue("AUTH_BEFORE_SCOPE", "authorization precedes scope declaration"))
            key = (payload.surface, payload.operation, payload.target)
            authorized[key] = payload.decision
        elif typ == "mutation.execution":
            key = (payload.surface, payload.operation, payload.target)
            if authorized.get(key) != "AUTHORIZED":
                issues.append(LifecycleIssue("EXECUTION_WITHOUT_AUTHORIZATION", ":".join(key)))
            executed[key] = payload.status
        elif typ == "mutation.verification":
            key = (payload.surface, payload.operation, payload.target)
            if executed.get(key) != "EXECUTED":
                issues.append(LifecycleIssue("VERIFICATION_WITHOUT_EXECUTION", ":".join(key)))

    if not scope_seen:
        issues.append(LifecycleIssue("MISSING_SCOPE_DECLARATION", "no scope declaration in stream"))

    return LifecycleValidation(valid=not issues, issues=tuple(issues))
