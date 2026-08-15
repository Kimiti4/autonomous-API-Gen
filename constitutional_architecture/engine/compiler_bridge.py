"""
Compiler Bridge — Connects evolved ISR to the 7-pass Compiler Pipeline.

Constitutional constraint:
- Imports from compiler.* to invoke the pipeline
- NEVER imports from engine.* internals
- Operates on ISR objects only
- The bridge is the ONLY module that connects engine → compiler
"""

from __future__ import annotations

from constitutional_architecture.compiler.pipeline import CompilationResult, CompilerConfig, CompilerPipeline
from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.isr import ISR


def compile_evolved_isr(
    isr: ISR,
    backend: str = "fastapi",
    output_dir: str = "./generated",
    package_name: str = "",
    generate_tests: bool = True,
    generate_docker: bool = True,
) -> CompilationResult:
    """
    Compile an evolved ISR through the 7-pass compiler pipeline.

    Ensures the evolved ISR is compiled into deployable artifacts,
    with the Capability Resolver mapping ISR needs to backend-specific
    implementations.
    """
    resolved_pkg = package_name or f"{isr.system.name.lower().replace('-', '_')}_app"

    config = CompilerConfig(
        backend=backend,
        output_dir=output_dir,
        package_name=resolved_pkg,
        generate_tests=generate_tests,
        generate_docker=generate_docker,
    )

    graph = _isr_to_graph_for_compiler(isr)
    pipeline = CompilerPipeline(config=config)
    return pipeline.compile(graph)


def _isr_to_graph_for_compiler(isr: ISR) -> TypedGraph:
    """Convert ISR model to TypedGraph for the compiler pipeline."""
    from constitutional_architecture.engine.isr_adapter import isr_to_graph
    return isr_to_graph(isr)
