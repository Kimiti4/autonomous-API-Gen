"""Phase 18 factory report types (pure dataclasses; tree types duck-typed)."""

from __future__ import annotations

from dataclasses import dataclass, field


class SoftwareFactoryError(RuntimeError):
    """Raised when the factory cannot produce a verified bundle."""

    def __init__(self, message: str, report: "SoftwareFactoryReport | None" = None) -> None:
        super().__init__(message)
        self.report = report


@dataclass(frozen=True)
class VerificationOutcome:
    bundle_backend_id: str
    static_ok: bool
    static_report: object | None
    test_result: object | None
    repair_attempts: int
    repaired: bool
    ok: bool


@dataclass(frozen=True)
class SoftwareFactoryReport:
    statement_hash: str
    isr_hash: str
    plan_id: str
    policy_name: str | None
    materialization: object | None
    verification_outcomes: tuple[VerificationOutcome, ...] = field(default_factory=tuple)
    fitness: object | None = None
    ok: bool = False
