"""Repair contracts for the Phase 18 software factory.

A RepairProvider diagnoses a verification failure and applies a bounded,
auditable correction to a materialized bundle. Repair is a *last-resort*,
narrowly-scoped mechanism: the constitutionally-preferred repair is
ISR-level refinement + recompilation (tracked as a follow-up, because
``compile_intent`` is not yet re-entrant with constraints). Code-level
repair handles defects not expressible at the ISR.

Providers must be deterministic and safe. Their output is always re-verified
by an independent verifier; the repairer is never trusted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RepairRequest:
    bundle_path: str
    failure_signature: str
    static_report: object | None
    test_result: object | None
    source_artifacts: dict[str, str]
    attempt: int
    max_attempts: int


@dataclass(frozen=True)
class RepairAction:
    operation: str
    target: str
    content: str | None = None
    description: str = ""


@dataclass(frozen=True)
class RepairReport:
    attempted: bool
    actions: tuple[RepairAction, ...]
    applied: bool
    reason: str | None = None


@runtime_checkable
class RepairProvider(Protocol):
    def diagnose(self, request: RepairRequest) -> tuple[RepairAction, ...]: ...

    def apply(self, bundle_path: str, actions: tuple[RepairAction, ...]) -> RepairReport: ...
