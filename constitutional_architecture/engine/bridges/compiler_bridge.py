from constitutional_architecture.compiler.pipeline import CompilationResult, CompilerConfig, CompilerPipeline
from constitutional_architecture.isr.graph.typed_graph import TypedGraph
from constitutional_architecture.isr.model.isr import ISR


class CompilerBridge:
    def compile(
        self,
        isr: ISR,
        backend: str = "fastapi",
        output_dir: str = "./generated",
        package_name: str = "",
        generate_tests: bool = True,
        generate_docker: bool = True,
    ) -> CompilationResult:
        project_name = isr.system.name.lower().replace('-', '_')
        resolved_pkg = package_name or f"{project_name}_app"
        config = CompilerConfig(
            project_name=project_name, target_backends=(backend,),
            output_dir=output_dir, package_name=resolved_pkg,
            generate_tests=generate_tests, generate_docker=generate_docker,
        )
        pipeline = CompilerPipeline()
        return pipeline.compile(isr, config=config)

    def _isr_to_graph(self, isr: ISR) -> TypedGraph:
        from constitutional_architecture.engine.isr_adapter import isr_to_graph
        return isr_to_graph(isr)
