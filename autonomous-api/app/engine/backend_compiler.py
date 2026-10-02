"""CAP-003 concrete backend compiler boundary.

A compiler maps technology-neutral BackendProjectIR to a declared target
language/framework. The compiler must not modify the ISR or architecture IR.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol
from .backend_ir import BackendProjectIR, validate_backend_ir


@dataclass(frozen=True)
class GeneratedArtifact:
    path: str
    content: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


@dataclass(frozen=True)
class BackendCompilation:
    target: str
    source_schema_version: str
    artifacts: tuple[GeneratedArtifact, ...]
    diagnostics: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "source_schema_version": self.source_schema_version,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "diagnostics": list(self.diagnostics),
        }


class BackendCompiler(Protocol):
    target: str

    def compile(self, ir: BackendProjectIR) -> BackendCompilation: ...


class TemplateBackendCompiler:
    """Small deterministic reference compiler; production compilers can replace it."""

    def __init__(self, target: str, source_extension: str):
        self.target = target
        self.source_extension = source_extension

    def compile(self, ir: BackendProjectIR) -> BackendCompilation:
        findings = validate_backend_ir(ir)
        if findings:
            return BackendCompilation(self.target, ir.schema_version, (), findings)
        artifacts: list[GeneratedArtifact] = []
        for component in ir.components:
            filename = f"src/{component.component_id}{self.source_extension}"
            body = (
                f"# generated component: {component.component_id}\n"
                f"# responsibility: {component.responsibility}\n"
                f"# architecture: {ir.architecture_id}\n"
            )
            artifacts.append(GeneratedArtifact(filename, body, "source"))
        artifacts.append(GeneratedArtifact(
            "config/schema.txt", "\n".join(ir.configuration_keys) + "\n", "configuration"
        ))
        artifacts.append(GeneratedArtifact(
            "contracts/errors.txt", ir.error_contract + "\n", "contract"
        ))
        return BackendCompilation(self.target, ir.schema_version, tuple(artifacts), ())


def compile_backend(ir: BackendProjectIR, compiler: BackendCompiler) -> BackendCompilation:
    return compiler.compile(ir)
