"""
Phase 15 — Deployment Meta-Compiler Base Contract
Meta-compilation: deployment concerns depend on produced artifacts, not
business intent. The Deployment Meta-Compiler operates on the assembled
SystemDeploymentBundle and compiles the final wiring (CI/CD pipelines,
container orchestration) that binds all bundles into one deployable artifact.

Constitutional Alignment:
- "Treat every framework and platform as a compiler backend."
- Single responsibility: application compilers produce bundles; meta-compilers
  assemble them. Neither depends on the other's internals.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from constitutional_architecture.core.models.bundle import (
    CompilationBundle, SystemDeploymentBundle,
)


class DeploymentMetaCompiler(ABC):
    @abstractmethod
    def compile_system(
        self,
        bundle: SystemDeploymentBundle,
        context: Dict[str, Any],
    ) -> CompilationBundle:
        pass
