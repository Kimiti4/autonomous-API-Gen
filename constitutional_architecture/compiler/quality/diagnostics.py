from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DiagnosticSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.INFO


class DiagnosticsCollector:
    def __init__(self) -> None:
        self._diagnostics: list[Diagnostic] = []

    def add(self, diagnostic: Diagnostic) -> None:
        self._diagnostics.append(diagnostic)

    def info(self, code: str, message: str) -> None:
        self._diagnostics.append(Diagnostic(code=code, message=message, severity=DiagnosticSeverity.INFO))

    def warning(self, code: str, message: str) -> None:
        self._diagnostics.append(Diagnostic(code=code, message=message, severity=DiagnosticSeverity.WARNING))

    def error(self, code: str, message: str) -> None:
        self._diagnostics.append(Diagnostic(code=code, message=message, severity=DiagnosticSeverity.ERROR))

    def fatal(self, code: str, message: str) -> None:
        self._diagnostics.append(Diagnostic(code=code, message=message, severity=DiagnosticSeverity.FATAL))

    @property
    def diagnostics(self) -> list[Diagnostic]:
        return list(self._diagnostics)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self._diagnostics if d.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.FATAL)]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self._diagnostics if d.severity == DiagnosticSeverity.WARNING]

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def total_count(self) -> int:
        return len(self._diagnostics)
