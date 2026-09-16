"""Compiler backend registry.

The registry is deliberately small: backend selection is a compiler concern,
not a Genome concern. Additional language/framework targets can implement the
same CompilerBackend contract without changing the ISR-facing model.
"""

from typing import Dict

from app.engine.backend_contract import (
    CompilerBackend,
    CompilationRequest,
    CompiledArtifact,
    PYTHON_FASTAPI,
)
from app.engine.builder import generate_main_app
from app.engine.genome import Genome


class PythonFastAPIBackend:
    """First concrete compiler backend for the existing Python generator."""

    target = PYTHON_FASTAPI

    def supports(self, request: CompilationRequest) -> bool:
        return request.target == self.target

    def compile(self, request: CompilationRequest) -> CompiledArtifact:
        if not self.supports(request):
            raise ValueError(
                f"unsupported backend target: {request.target.backend_id}"
            )
        # Technology-specific interpretation stays here. The architecture
        # request itself remains unchanged and is never mutated by the backend.
        genome = Genome(dict(request.architecture))
        source = generate_main_app(genome)
        return CompiledArtifact(
            backend_id=self.target.backend_id,
            files={"main.py": source},
            metadata={
                "language": self.target.language,
                "framework": self.target.framework,
            },
        )


_BACKENDS: Dict[str, CompilerBackend] = {
    PYTHON_FASTAPI.backend_id: PythonFastAPIBackend(),
}


def get_backend(backend_id: str) -> CompilerBackend:
    """Resolve an explicitly selected compiler backend; fail closed otherwise."""

    try:
        return _BACKENDS[backend_id]
    except KeyError as exc:
        raise ValueError(f"unknown compiler backend: {backend_id}") from exc


def compile_architecture(request: CompilationRequest) -> CompiledArtifact:
    """Compile using only the backend explicitly present in the request."""

    return get_backend(request.target.backend_id).compile(request)
