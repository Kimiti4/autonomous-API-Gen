"""compiler.core — technology-neutral compiler substrate (ADR-012)."""

from compiler.core.canonical_ir import CompilerIR, CompilerIRNode, CompilerIRRelationship
from compiler.core.plan import CompilationPlan

__all__ = [
    "CompilerIR",
    "CompilerIRNode",
    "CompilerIRRelationship",
    "CompilationPlan",
]
