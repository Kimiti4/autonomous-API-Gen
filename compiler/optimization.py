"""
Compiler optimization pipeline.

The optimization pipeline executes deterministic passes before backend
compilation.

The initial passes are conservative. Future passes may include:
- architecture normalization
- capability alignment
- backend constraint resolution
- cost optimization
- reliability hardening
- observability enrichment
"""

from __future__ import annotations

from typing import Any, Protocol

from .models import CompilationPlan


class OptimizationPass(Protocol):
    """Contract for compiler optimization passes."""

    name: str

    def apply(
        self,
        plan: CompilationPlan,
        isr: dict[str, Any],
        logs: list[str],
    ) -> None:
        ...


class NormalizeCompilationParametersPass:
    """Normalizes compilation parameters."""

    name = "normalize_compilation_parameters"

    def apply(
        self,
        plan: CompilationPlan,
        isr: dict[str, Any],
        logs: list[str],
    ) -> None:
        plan.parameters.setdefault("include_manifest", True)
        plan.parameters.setdefault("deterministic_output", True)

        logs.append("Normalized compilation parameters.")


class ValidateDomainStructurePass:
    """Performs lightweight structural inspection of ISR domains."""

    name = "validate_domain_structure"

    def apply(
        self,
        plan: CompilationPlan,
        isr: dict[str, Any],
        logs: list[str],
    ) -> None:
        domains = isr.get("domains")

        if not domains:
            logs.append("ISR contains no domains.")
            return

        unnamed_domains = 0

        for domain in domains:
            if not isinstance(domain, dict):
                continue

            if not domain.get("name"):
                unnamed_domains += 1

        if unnamed_domains:
            logs.append(
                f"Detected {unnamed_domains} unnamed domain(s) in ISR."
            )
        else:
            logs.append("Domain structure inspection completed.")


class OptimizationPipeline:
    """Executes optimization passes."""

    def __init__(
        self,
        passes: list[OptimizationPass] | None = None,
    ) -> None:
        self._passes = passes or [
            NormalizeCompilationParametersPass(),
            ValidateDomainStructurePass(),
        ]

    def run(
        self,
        plan: CompilationPlan,
        isr: dict[str, Any],
        logs: list[str],
    ) -> list[str]:
        executed: list[str] = []

        for optimization_pass in self._passes:
            optimization_pass.apply(plan, isr, logs)
            executed.append(optimization_pass.name)

        return executed