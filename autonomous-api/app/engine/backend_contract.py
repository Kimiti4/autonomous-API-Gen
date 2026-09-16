"""Technology-neutral compiler backend contract.

The Genome remains the source of architectural intent. Backend selection is a
compiler concern and therefore lives outside the Genome. A backend consumes a
validated architectural representation and produces an implementation artifact;
it must not mutate or reinterpret the architectural input.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence


@dataclass(frozen=True)
class BackendTarget:
    """A compiler target, independent of the architecture genome."""

    backend_id: str
    language: str
    framework: str
    version: str = "1"


@dataclass(frozen=True)
class CompilationRequest:
    """Immutable hand-off from architecture selection to a compiler backend."""

    target: BackendTarget
    architecture: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.target.backend_id.strip():
            raise ValueError("backend_id must not be empty")
        if not self.target.language.strip():
            raise ValueError("language must not be empty")
        if not self.target.framework.strip():
            raise ValueError("framework must not be empty")
        if not isinstance(self.architecture, Mapping):
            raise TypeError("architecture must be a mapping")


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
