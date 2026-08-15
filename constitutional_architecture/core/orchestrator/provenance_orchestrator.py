"""
Phase 16 — Provenance-Aware Orchestrator
Executes the Compiler DAG, checks the content-addressable cache before every
compile step (incremental builds), and stamps immutable ArtifactProvenance on
every generated bundle.

Second-Generation Status:
- Compiler DAG: hardcoded phases eliminated; compilers declare dependencies.
- Incremental compilation: cache hits skip compilation entirely.
- Provenance: every bundle is cryptographically linked to the Intent, Genome,
  ISR, and Compiler Version that created it — the precondition for the
  Runtime Learning Engine (Phase 18).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from constitutional_architecture.compilers.deployment.base import DeploymentMetaCompiler
from constitutional_architecture.core.build.dag import BuildGraphResolver
from constitutional_architecture.core.build.provenance import (
    ArtifactProvenance, EvolutionaryBuildCache, bundle_hash, genome_signature,
    intent_signature, isr_signature,
)
from constitutional_architecture.core.models.bundle import (
    ArtifactType, CompilationBundle, SystemDeploymentBundle,
)
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import IntentModel
from constitutional_architecture.core.models.isr import UniversalISR


class ProvenanceOrchestrator:
    def __init__(
        self,
        resolver: BuildGraphResolver,
        cache: EvolutionaryBuildCache,
    ) -> None:
        self.resolver = resolver
        self.cache = cache

    def compile_system(
        self,
        intent: IntentModel,
        genome: ArchitectureGenome,
        isr: UniversalISR,
        target_artifacts: Set[ArtifactType],
        eligible_ids: Optional[Set[str]] = None,
    ) -> SystemDeploymentBundle:
        execution_plan = self.resolver.resolve_execution_plan(
            target_artifacts, eligible_ids,
        )

        compiled_bundles: Dict[str, CompilationBundle] = {}
        execution_context: Dict[str, Any] = {
            "project_name": intent.project_name,
            "intent": intent,
        }
        provenance_records: Dict[str, Dict[str, Any]] = {}

        for comp_id in execution_plan:
            node = self.resolver.nodes[comp_id]
            compiler = node.compiler_class()
            version = getattr(compiler, "VERSION", "1.0.0")

            input_hashes = sorted({
                bundle_hash(compiled_bundles[dep_id])
                for req in node.requires
                for dep_id in self.resolver.providers.get(req, [])
                if dep_id in compiled_bundles
            })

            isr_h = isr_signature(isr, node.consumed_node_types)
            genome_h = genome_signature(genome, node.consumed_genes)
            intent_h = isr.intent_hash or intent_signature(intent)

            cache_key = self.cache.compute_cache_key(
                compiler_id=comp_id,
                compiler_version=version,
                isr_hash=isr_h,
                genome_hash=genome_h,
                input_bundle_hashes=input_hashes,
            )

            cached_bundle = self.cache.get(cache_key)
            if cached_bundle is not None:
                # CACHE HIT — incremental compilation: skip the compiler.
                compiled_bundles[comp_id] = cached_bundle
                execution_context.update(cached_bundle.exposed_interfaces)
                provenance_records[comp_id] = self.cache.provenance_of(cache_key).model_dump()
                continue

            if isinstance(compiler, DeploymentMetaCompiler):
                system = SystemDeploymentBundle(
                    project_name=intent.project_name,
                    bundles=compiled_bundles,
                )
                bundle = compiler.compile_system(system, execution_context)
            else:
                bundle = compiler.compile(isr, genome, execution_context)

            provenance = ArtifactProvenance(
                artifact_hash=bundle_hash(bundle),
                compiler_id=comp_id,
                compiler_version=version,
                genome_id=genome.genome_id or "unknown",
                genome_hash=genome_h,
                isr_hash=isr_h,
                intent_hash=intent_h,
                timestamp=datetime.now(timezone.utc),
                input_dependencies=input_hashes,
            )

            self.cache.put(cache_key, bundle, provenance)
            compiled_bundles[comp_id] = bundle
            execution_context.update(bundle.exposed_interfaces)
            provenance_records[comp_id] = provenance.model_dump()

        return SystemDeploymentBundle(
            project_name=intent.project_name,
            bundles=compiled_bundles,
            global_metadata={"provenance": provenance_records},
        )
