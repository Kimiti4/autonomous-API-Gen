"""Frontend compiler registry.

Frontend IR remains platform-neutral. Registry entries are target metadata;
they do not become architectural authority.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .frontend_ir import FrontendProjectIR, validate_frontend_ir


@dataclass(frozen=True)
class FrontendCompilation:
    target: str
    source_schema_version: str
    artifacts: tuple[object, ...]
    diagnostics: tuple[str, ...] = ()


class FrontendCompiler(Protocol):
    target: str
    def compile(self, ir: FrontendProjectIR) -> FrontendCompilation: ...


@dataclass(frozen=True)
class FrontendTarget:
    target_id: str
    platform: str
    language: str
    framework: str | None = None


class FrontendCompilerRegistry:
    def __init__(self) -> None:
        self._targets: dict[str, tuple[FrontendTarget, FrontendCompiler]] = {}

    def register(self, target: FrontendTarget, compiler: FrontendCompiler) -> None:
        if target.target_id in self._targets:
            raise ValueError(f"frontend target already registered: {target.target_id}")
        if compiler.target != target.target_id:
            raise ValueError("compiler target does not match registry target")
        self._targets[target.target_id] = (target, compiler)

    def targets(self) -> tuple[FrontendTarget, ...]:
        return tuple(x[0] for x in self._targets.values())

    def compile(self, target_id: str, ir: FrontendProjectIR) -> FrontendCompilation:
        if target_id not in self._targets:
            raise KeyError(f"unknown frontend target: {target_id}")
        findings = validate_frontend_ir(ir)
        if findings:
            return FrontendCompilation(target_id, ir.schema_version, (), findings)
        return self._targets[target_id][1].compile(ir)
