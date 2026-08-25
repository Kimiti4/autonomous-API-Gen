"""CompilerBackend — the technology-independent plugin protocol."""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from compiler.core.plan import CompilationPlan
from compiler.core.repository import GeneratedRepository
from compiler.core.conformance import ConformanceReport


@runtime_checkable
class CompilerBackend(Protocol):
    """Every backend must implement this protocol. The core never imports
    a concrete backend — only this protocol."""
    name: str
    language: str
    framework: str
    version: str

    def element_paths(self, plan: CompilationPlan) -> dict[str, str]: ...
    def compile(self, plan: CompilationPlan) -> GeneratedRepository: ...
    def conformance(self, plan: CompilationPlan, repo: GeneratedRepository) -> ConformanceReport: ...
