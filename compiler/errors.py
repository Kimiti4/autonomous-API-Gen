"""
Compiler error model.
"""

from __future__ import annotations


class CompilerError(Exception):
    """Base compiler error."""


class BackendNotFoundError(CompilerError):
    """Raised when a requested backend is not registered."""


class BackendRegistrationError(CompilerError):
    """Raised when backend registration fails."""


class ISRValidationError(CompilerError):
    """Raised when ISR payload fails validation."""

    def __init__(self, message: str, report) -> None:
        super().__init__(message)
        self.report = report


class CompilationOutputValidationError(CompilerError):
    """Raised when backend output fails validation."""

    def __init__(self, message: str, report) -> None:
        super().__init__(message)
        self.report = report


class ArtifactPackagingError(CompilerError):
    """Raised when artifact packaging fails."""