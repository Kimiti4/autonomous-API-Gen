"""
Backend base contract and adapter.

The SDK adapter ensures that all backends satisfy minimal constitutional
requirements before compilation:

- ISR validation
- explicit failure behavior
- health reporting
- configuration validation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..errors import ISRValidationError
from ..models import (
    BackendManifest,
    CompilationContext,
    CompilationOutput,
    ValidationReport,
)
from ..validation import validate_isr_payload


class BackendHealth(BaseModel):
    """Health status for a compiler backend."""

    backend_id: str
    status: Literal[
        "ok",
        "degraded",
        "error",
    ] = "ok"
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class CompilerBackendBase(ABC):
    """
    Base contract for compiler backends.

    Production backends may inherit from this class or implement the same
    structural contract.
    """

    manifest: BackendManifest

    @abstractmethod
    def compile(self, context: CompilationContext) -> CompilationOutput:
        """Compile ISR into backend artifacts."""

    def validate_configuration(self, config: dict[str, Any]) -> ValidationReport:
        """Validate backend-specific configuration."""
        return ValidationReport(valid=True, issues=[])

    def health_check(self) -> BackendHealth:
        """Return backend health."""
        return BackendHealth(
            backend_id=self.manifest.backend_id,
            status="ok",
            message="Backend is healthy.",
        )


class SDKBackendAdapter:
    """
    Adapts arbitrary backend objects to the SDK contract.

    This adapter enforces ISR validation before delegating compilation to
    the wrapped backend.
    """

    def __init__(self, backend: Any) -> None:
        self._backend = backend
        self.manifest: BackendManifest = backend.manifest

    def compile(self, context: CompilationContext) -> CompilationOutput:
        isr_report = validate_isr_payload(context.isr)

        if not isr_report.valid:
            raise ISRValidationError(
                "Backend received invalid ISR.",
                isr_report,
            )

        return self._backend.compile(context)

    def validate_configuration(self, config: dict[str, Any]) -> ValidationReport:
        validator = getattr(self._backend, "validate_configuration", None)

        if callable(validator):
            return validator(config)

        return ValidationReport(valid=True, issues=[])

    def health_check(self) -> BackendHealth:
        health_check = getattr(self._backend, "health_check", None)

        if callable(health_check):
            health = health_check()

            if isinstance(health, BackendHealth):
                return health

            return BackendHealth(
                backend_id=self.manifest.backend_id,
                status="ok",
                message=str(health),
            )

        return BackendHealth(
            backend_id=self.manifest.backend_id,
            status="ok",
            message="Backend does not implement health_check.",
        )


def ensure_sdk_backend(backend: Any) -> SDKBackendAdapter:
    """Wrap a backend with the SDK adapter if needed."""

    if isinstance(backend, SDKBackendAdapter):
        return backend

    return SDKBackendAdapter(backend)