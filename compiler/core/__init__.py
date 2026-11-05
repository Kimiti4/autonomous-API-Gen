"""compiler.core — technology-neutral compiler substrate (ADR-012)."""

from compiler.core.canonical_ir import (
    CompilerIR, CompilerIRNode, CompilerIRRelationship,
    CompilerIRProjectionReport, assert_compiler_ir_supported,
)
from compiler.core.plan import CompilationPlan

__all__ = [
    "CompilerIR",
    "CompilerIRNode",
    "CompilerIRRelationship",
    "CompilerIRProjectionReport",
    "assert_compiler_ir_supported",
    "CompilationPlan",
]
