"""
Compiler — Pipeline from ISR to Production Code.
"""

from constitutional_architecture.compiler.compilation_config import CompilationConfig, OptimizationLevel
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.compiler_result import CompilationResult, CapabilityReport, VerificationResult
from constitutional_architecture.compiler.pass_interface import CompilerPass, PassResult
from constitutional_architecture.compiler.pass_registry import PassRegistry
from constitutional_architecture.compiler.pass_manager import PassManager
from constitutional_architecture.compiler.pipeline import CompilerPipeline, build_default_pipeline
from constitutional_architecture.compiler.capability import CapabilityResolver, CapabilityMap, Capability, BackendCapabilities
from constitutional_architecture.compiler.contract import CompilationArtifact, CompilerBackend


def FastAPIBackend(*args, **kwargs):
    from constitutional_architecture.compiler.backends.fastapi_backend import FastAPIBackend as _cls
    return _cls(*args, **kwargs)


CompilerConfig = CompilationConfig

__all__ = [
    "CompilerPipeline", "CompilerPass", "PassResult", "CompilationResult", "CompilationConfig",
    "CompilerConfig", "OptimizationLevel", "CompilerContext", "PassRegistry", "PassManager",
    "CapabilityResolver", "CapabilityMap", "Capability", "BackendCapabilities",
    "FastAPIBackend", "CapabilityReport", "VerificationResult", "build_default_pipeline",
    "CompilationArtifact", "CompilerBackend",
]
