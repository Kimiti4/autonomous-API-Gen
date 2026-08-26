"""CompilerBackend — the technology-independent plugin protocol.

Defines the backend contract plus certification class enforcement.
A stub or structural backend can NEVER award behavioral certification.
"""
from __future__ import annotations
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from compiler.core.plan import CompilationPlan
from compiler.core.repository import GeneratedRepository
from compiler.core.conformance import ConformanceReport


class BackendClass(str, Enum):
    STUB = "stub"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    PRODUCTION = "production"


BEHAVIORAL_CLASSES = frozenset({BackendClass.BEHAVIORAL, BackendClass.PRODUCTION})


class BackendIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    language: str
    framework: str
    version: str
    backend_class: BackendClass


def eligible_for_behavioral_certification(identity: BackendIdentity) -> bool:
    return identity.backend_class in BEHAVIORAL_CLASSES


@runtime_checkable
class CompilerBackend(Protocol):
    """Every backend must implement this protocol. The core never imports
    a concrete backend — only this protocol."""
    name: str
    language: str
    framework: str
    version: str

    def identity(self) -> BackendIdentity: ...
    def element_paths(self, plan: CompilationPlan) -> dict[str, str]: ...
    def compile(self, plan: CompilationPlan) -> GeneratedRepository: ...
    def conformance(self, plan: CompilationPlan, repo: GeneratedRepository) -> ConformanceReport: ...
