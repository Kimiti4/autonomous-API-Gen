"""Technology-neutral compiler backend contract.

The Genome remains the source of architectural intent. Backend selection is a
compiler concern and therefore lives outside the Genome. A backend consumes a
validated architectural representation and produces an implementation artifact;
it must not mutate or reinterpret the architectural input.

The architecture mapping handed to a backend is validated against a canonical
schema at the boundary. Drift — a mutated, extended or mistyped architecture —
fails closed instead of being silently reinterpreted.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

ARCHITECTURE_SCHEMA_VERSION = "genome-v1"

# Canonical keys the compiler boundary accepts from the architecture authority.
# Missing values are tolerated (the Genome applies its defaults); *unknown* keys
# and *wrongly typed* values are drift and must fail closed.
_ARCHITECTURE_KEYS = {
    "genome_id": str,
    "services": list,
    "auth": str,
    "database": str,
    "cache_enabled": bool,
    "rate_limiting": bool,
    "cors_enabled": bool,
    "logging_level": str,
    "api_version": str,
    "security_score": (int, float),
    "openapi_version": str,
    "health_endpoints": bool,
    "metrics_endpoints": bool,
    "tracing_enabled": bool,
    "circuit_breaker": bool,
    "retry_policy": dict,
    "timeout_config": dict,
    "backends": list,
    "middleware": list,
    "security_policies": list,
    "metrics": dict,
    "blueprints_used": list,
    "policies_applied": list,
    "deployment_target": str,
    "lineage": dict,
}

_REQUIRED_ARCHITECTURE_KEYS: tuple[str, ...] = ("services", "auth", "database")


def validate_architecture(architecture: Mapping[str, Any]) -> None:
    """Validate an architecture mapping against the canonical compiler schema.

    Fails closed on unknown keys (architecture drift), mistyped values, and
    missing required keys. Does not mutate the mapping.
    """
    if not isinstance(architecture, Mapping):
        raise TypeError("architecture must be a mapping")

    unknown = set(architecture) - set(_ARCHITECTURE_KEYS)
    if unknown:
        raise ValueError(f"architecture drift: unknown keys {sorted(unknown)}")

    for key in _REQUIRED_ARCHITECTURE_KEYS:
        if key not in architecture:
            raise ValueError(f"architecture missing required key: {key!r}")

    for key, expected in _ARCHITECTURE_KEYS.items():
        if key not in architecture:
            continue
        value = architecture[key]
        if not isinstance(value, expected):
            raise ValueError(
                f"architecture drift: key {key!r} has type {type(value).__name__}, "
                f"expected {expected!r}"
            )


@dataclass(frozen=True)
class BackendTarget:
    """A compiler target, independent of the architecture genome."""

    backend_id: str
    language: str
    framework: str
    version: str = "1"


@dataclass(frozen=True)
class CompilationRequest:
    """Immutable hand-off from architecture selection to a compiler backend.

    The architecture is validated against the canonical schema on construction
    so a drifted architecture can never reach a backend.
    """

    target: BackendTarget
    architecture: Mapping[str, Any]
    architecture_schema: str = ARCHITECTURE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.target.backend_id.strip():
            raise ValueError("backend_id must not be empty")
        if not self.target.language.strip():
            raise ValueError("language must not be empty")
        if not self.target.framework.strip():
            raise ValueError("framework must not be empty")
        if not self.architecture_schema.strip():
            raise ValueError("architecture_schema must not be empty")
        validate_architecture(self.architecture)


@dataclass(frozen=True)
class CompiledArtifact:
    """Backend output with no architectural mutation channel."""

    backend_id: str
    files: Mapping[str, str]
    metadata: Mapping[str, Any]


class CompilerBackend(Protocol):
    """Minimal interface implemented by language/framework compiler plugins."""

    target: BackendTarget

    def compile(self, request: CompilationRequest) -> CompiledArtifact:
        """Lower an immutable architecture request into an implementation."""
        ...

    def supports(self, request: CompilationRequest) -> bool:
        """Report whether this backend can compile the requested target."""
        ...


PYTHON_FASTAPI = BackendTarget(
    backend_id="python-fastapi",
    language="python",
    framework="fastapi",
)


def make_compilation_request(
    architecture: Mapping[str, Any], target: BackendTarget = PYTHON_FASTAPI
) -> CompilationRequest:
    """Create the compiler hand-off without embedding target data in the Genome."""

    return CompilationRequest(target=target, architecture=dict(architecture))