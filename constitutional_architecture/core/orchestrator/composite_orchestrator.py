from __future__ import annotations

from typing import Any, Dict, List

from constitutional_architecture.compilers.deployment.base import DeploymentMetaCompiler
from constitutional_architecture.core.models.bundle import (
    CompilationBundle, SystemDeploymentBundle,
)
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import IntentModel
from constitutional_architecture.core.models.isr import UniversalISR
from constitutional_architecture.core.registry.compiler_registry import CompilerRegistry


class OrchestrationError(Exception):
    pass


class CompositeOrchestrator:
    """Two-pass orchestration: application/infrastructure/cross-cutting compilers
    first (dependency-ordered by context propagation), meta-compilers last —
    they assemble the produced SystemDeploymentBundle into deployable artifacts.
    """

    def __init__(self, registry: CompilerRegistry) -> None:
        self.registry = registry

    def compile_system(
        self,
        intent: IntentModel,
        genome: ArchitectureGenome,
        isr: UniversalISR,
    ) -> SystemDeploymentBundle:
        compiler_ids = self.registry.resolve_compilers(genome, isr)
        meta_compiler_ids = self.registry.resolve_meta_compilers()
        if not compiler_ids and not meta_compiler_ids:
            raise OrchestrationError("No compilers resolved for the given Genome/ISR.")

        execution_context: Dict[str, Any] = {
            "project_name": intent.project_name,
            "intent": intent,
        }

        bundles: Dict[str, CompilationBundle] = {}

        for comp_id in compiler_ids:
            compiler = self.registry.get_compiler(comp_id)
            bundle = compiler.compile(isr, genome, execution_context)
            bundles[comp_id] = bundle
            execution_context.update(bundle.exposed_interfaces)

        system = SystemDeploymentBundle(
            project_name=intent.project_name,
            bundles=bundles,
        )

        for comp_id in meta_compiler_ids:
            compiler = self.registry.get_compiler(comp_id)
            if not isinstance(compiler, DeploymentMetaCompiler):
                continue
            meta_bundle = compiler.compile_system(system, execution_context)
            bundles[comp_id] = meta_bundle

        return SystemDeploymentBundle(
            project_name=intent.project_name,
            bundles=bundles,
        )
