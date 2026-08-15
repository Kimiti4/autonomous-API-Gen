"""Intent compilation error taxonomy.

All errors carry enough context to be actionable and auditable.
``RepairBudgetExceeded`` is deliberately distinct from validation errors so
callers can distinguish "structurally invalid but repairable" from
"repair exhausted".
"""

from __future__ import annotations


class IntentCompilationError(Exception):
    """Base error for intent compilation failures."""


class RepairBudgetExceeded(IntentCompilationError):
    """Raised when the bounded repair loop exhausts its iterations."""

    def __init__(self, issues: list[str], iterations: int) -> None:
        self.issues = list(issues)
        self.iterations = iterations
        super().__init__(
            f"Requirement graph still invalid after {iterations} repair "
            f"iteration(s). Outstanding issues: {issues}"
        )
