"""
Phase 16 — Compiler Dependency Graph (DAG) & Topological Resolver
Enables dynamic scheduling, parallelism, and incremental builds.

Compilers no longer belong to static "phases". They declare what they `require`
and what they `provide`. The orchestrator resolves the execution order
dynamically.

Constitutional Alignment:
- "Treat every framework and platform as a compiler backend."
- Replaces hardcoded phase lists with a declarative, self-scheduling build graph.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Type

from constitutional_architecture.compilers.backend.fastapi.compiler import FastAPICompiler
from constitutional_architecture.compilers.database.postgres.compiler import PostgresCompiler
from constitutional_architecture.compilers.deployment.cicd.compiler import CICDDeploymentCompiler
from constitutional_architecture.compilers.documentation.markdown.compiler import (
    MarkdownDocumentationCompiler,
)
from constitutional_architecture.compilers.frontend.react.compiler import ReactCompiler
from constitutional_architecture.compilers.infrastructure.terraform.compiler import (
    TerraformCompiler,
)
from constitutional_architecture.compilers.operational.intelligence.compiler import (
    OperationalIntelligenceCompiler,
)
from constitutional_architecture.compilers.runtime_policy.compiler import RuntimePolicyCompiler
from constitutional_architecture.compilers.testing.pytest.compiler import PytestCompiler
from constitutional_architecture.core.contracts.compiler import CompilerBackend
from constitutional_architecture.core.models.bundle import ArtifactType
from constitutional_architecture.core.models.isr import NodeType


class CompilerNode:
    """A node in the build graph representing a compiler plugin."""

    def __init__(
        self,
        compiler_id: str,
        compiler_class: Type[CompilerBackend],
        provides: List[ArtifactType],
        requires: List[ArtifactType],
        consumed_genes: Optional[List[str]] = None,
        consumed_node_types: Optional[List[NodeType]] = None,
    ) -> None:
        self.compiler_id = compiler_id
        self.compiler_class = compiler_class
        self.provides = set(provides)
        self.requires = set(requires)
        # Declared input scope for incremental hashing. None = whole ISR/Genome
        # (always correct); [] = the compiler consumes no ISR/Genome state
        # (its inputs are exclusively bundles). Anything else scopes the cache
        # key to exactly the genes/node types consumed — the Bazel contract.
        self.consumed_genes = consumed_genes
        self.consumed_node_types = consumed_node_types


class BuildGraphResolver:
    """Resolves compiler execution order from artifact-level dependencies."""

    def __init__(self) -> None:
        self.nodes: Dict[str, CompilerNode] = {}
        # Maps an ArtifactType to every compiler_id that provides it.
        # Multiple providers are permitted (e.g., React and FastAPI both
        # provide SOURCE_CODE); eligibility decides which join the plan.
        self.providers: Dict[ArtifactType, List[str]] = defaultdict(list)

    def register(self, node: CompilerNode) -> None:
        if node.compiler_id in self.nodes:
            raise ValueError(f"Compiler '{node.compiler_id}' already registered.")
        self.nodes[node.compiler_id] = node
        for artifact in node.provides:
            self.providers[artifact].append(node.compiler_id)

    def resolve_execution_plan(
        self,
        target_artifacts: Set[ArtifactType],
        eligible_ids: Optional[Set[str]] = None,
    ) -> List[str]:
        """Backward traversal from desired artifacts, then Kahn topological sort.

        Returns a topologically sorted execution plan (dependencies before
        dependents).
        """
        eligible = set(eligible_ids) if eligible_ids is not None else set(self.nodes)

        required_compilers: Set[str] = set()
        queue: deque = deque(target_artifacts)

        while queue:
            artifact = queue.popleft()
            providers = [cid for cid in self.providers.get(artifact, []) if cid in eligible]
            if not providers:
                raise ValueError(f"No eligible compiler registered to provide: {artifact}")

            for comp_id in providers:
                if comp_id not in required_compilers:
                    required_compilers.add(comp_id)
                    queue.extend(self.nodes[comp_id].requires)

        in_degree = {cid: 0 for cid in required_compilers}
        graph: Dict[str, List[str]] = defaultdict(list)

        for cid in required_compilers:
            node = self.nodes[cid]
            for req_artifact in node.requires:
                for dep_cid in self.providers.get(req_artifact, []):
                    if dep_cid in required_compilers:
                        graph[dep_cid].append(cid)
                        in_degree[cid] += 1

        exec_queue = deque([cid for cid, degree in in_degree.items() if degree == 0])
        execution_plan: List[str] = []

        while exec_queue:
            cid = exec_queue.popleft()
            execution_plan.append(cid)
            for neighbor in graph[cid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    exec_queue.append(neighbor)

        if len(execution_plan) != len(required_compilers):
            raise RuntimeError("Cyclic dependency detected in Compiler DAG!")

        return execution_plan


def build_platform_graph() -> BuildGraphResolver:
    """Wires the full platform compiler set into a declarative build graph."""
    resolver = BuildGraphResolver()

    resolver.register(CompilerNode(
        "react_vite", ReactCompiler, [ArtifactType.SOURCE_CODE], [],
    ))
    resolver.register(CompilerNode(
        "fastapi_hexagonal", FastAPICompiler, [ArtifactType.SOURCE_CODE], [],
    ))
    resolver.register(CompilerNode(
        "postgres_alembic", PostgresCompiler, [ArtifactType.DATABASE_MIGRATION], [],
    ))
    resolver.register(CompilerNode(
        "terraform_aws", TerraformCompiler, [ArtifactType.INFRASTRUCTURE], [],
    ))
    resolver.register(CompilerNode(
        "markdown_adr", MarkdownDocumentationCompiler, [ArtifactType.DOCUMENTATION], [],
    ))
    resolver.register(CompilerNode(
        "operational_intelligence_v1",
        OperationalIntelligenceCompiler,
        [ArtifactType.CONFIGURATION], [],
    ))
    resolver.register(CompilerNode(
        "runtime_policy_v1", RuntimePolicyCompiler, [ArtifactType.CONFIGURATION], [],
    ))
    resolver.register(CompilerNode(
        "pytest_layered", PytestCompiler, [ArtifactType.TEST_SUITE], [],
    ))
    resolver.register(CompilerNode(
        "github_actions_compose",
        CICDDeploymentCompiler,
        [ArtifactType.CI_CD_PIPELINE],
        [
            ArtifactType.SOURCE_CODE,
            ArtifactType.INFRASTRUCTURE,
            ArtifactType.DATABASE_MIGRATION,
            ArtifactType.TEST_SUITE,
            ArtifactType.DOCUMENTATION,
            ArtifactType.CONFIGURATION,
        ],
        consumed_genes=[],
        consumed_node_types=[],
    ))

    return resolver
