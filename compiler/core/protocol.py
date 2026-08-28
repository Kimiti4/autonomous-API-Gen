"""CompilerBackend — the technology-independent plugin protocol.

Defines the backend contract plus certification class enforcement.
A stub or structural backend can NEVER award behavioral certification.
"""
from __future__ import annotations
from enum import Enum
from typing import Literal, Protocol, runtime_checkable

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


class TestSpec(BaseModel):
    """Declares how a backend's generated repository tests execute.

    The runner dispatches on this — never hardcodes a test command.
    """
    model_config = ConfigDict(frozen=True)
    __test__ = False  # not a pytest test class
    command: list[str]
    runs_in: Literal["runtime", "build"] = "runtime"
    build_target: str = "build"


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
    def test_spec(self) -> TestSpec: ...
    def element_paths(self, plan: CompilationPlan) -> dict[str, str]: ...
    def compile(self, plan: CompilationPlan) -> GeneratedRepository: ...
    def conformance(self, plan: CompilationPlan, repo: GeneratedRepository) -> ConformanceReport: ...
