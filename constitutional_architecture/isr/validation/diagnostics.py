"""
Compiler Diagnostics.

Provides diagnostic reporting similar to modern language compilers.
Every diagnostic includes code, message, severity, location, and suggested fix.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional


@unique
class DiagnosticSeverity(str, Enum):
    """Severity level of a diagnostic."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"

    def __str__(self) -> str:
        return self.value

    @property
    def is_error_or_above(self) -> bool:
        return self in {DiagnosticSeverity.ERROR, DiagnosticSeverity.FATAL}


@dataclass(frozen=True)
class DiagnosticLocation:
    """Location of a diagnostic within the ISR."""

    node_id: str = ""
    node_type: str = ""
    path: str = ""
    edge_id: Optional[str] = None


@dataclass(frozen=True)
class Diagnostic:
    """
    A single compiler diagnostic.

    Analogous to a compiler error/warning message with full context.
    """

    code: str
    message: str
    severity: DiagnosticSeverity
    location: DiagnosticLocation = field(default_factory=DiagnosticLocation)
    suggested_fix: str = ""
    related_nodes: tuple[str, ...] = ()
    documentation_url: str = ""

    def __str__(self) -> str:
        severity_str = self.severity.value.upper()
        loc_str = f" at {self.location.path}" if self.location.path else ""
        fix_str = f"\n  Suggested fix: {self.suggested_fix}" if self.suggested_fix else ""
        return f"[{self.code}] {severity_str}{loc_str}: {self.message}{fix_str}"


class DiagnosticsCollector:
    """Collects diagnostics during compilation or validation."""

    def __init__(self) -> None:
        self._diagnostics: list[Diagnostic] = []

    def add(self, diagnostic: Diagnostic) -> None:
        self._diagnostics.append(diagnostic)

    def add_error(self, code: str, message: str, **kwargs) -> None:
        self._diagnostics.append(Diagnostic(
            code=code,
            message=message,
            severity=DiagnosticSeverity.ERROR,
            **kwargs,
        ))

    def add_warning(self, code: str, message: str, **kwargs) -> None:
        self._diagnostics.append(Diagnostic(
            code=code,
            message=message,
            severity=DiagnosticSeverity.WARNING,
            **kwargs,
        ))

    def add_info(self, code: str, message: str, **kwargs) -> None:
        self._diagnostics.append(Diagnostic(
            code=code,
            message=message,
            severity=DiagnosticSeverity.INFO,
            **kwargs,
        ))

    @property
    def diagnostics(self) -> list[Diagnostic]:
        return list(self._diagnostics)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self._diagnostics if d.severity.is_error_or_above]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self._diagnostics if d.severity == DiagnosticSeverity.WARNING]

    @property
    def has_errors(self) -> bool:
        return any(d.severity.is_error_or_above for d in self._diagnostics)

    @property
    def count(self) -> int:
        return len(self._diagnostics)

    def clear(self) -> None:
        self._diagnostics.clear()
