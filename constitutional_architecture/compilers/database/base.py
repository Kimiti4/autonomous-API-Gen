"""
Phase 10 — Database Compiler Base Contract
Compiles the ISR Data Domain Graph into Logical Schemas, Physical DDL, and Migrations.

The database schema is a compiled artifact of the ISR — never a byproduct of an ORM.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict

from constitutional_architecture.core.contracts.compiler import CompilerBackend
from constitutional_architecture.core.models.bundle import CompilationBundle
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.isr import UniversalISR


class DatabaseCompiler(CompilerBackend):
    @abstractmethod
    def compile(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        context: Dict[str, Any],
    ) -> CompilationBundle:
        pass
