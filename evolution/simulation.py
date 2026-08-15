"""
Architecture simulation engine.

This simulator performs deterministic static analysis on candidate ISR
structures.
"""

from __future__ import annotations

from typing import Any

from .models import CandidateArchitecture, SimulationIssue, SimulationResult, utcnow
from .utils import deterministic_id, iter_data_models, iter_services


class ArchitectureSimulator:
    """Simulates architectural consequences of candidate ISR mutations."""

    def simulate(
        self,
        candidate: CandidateArchitecture,
    ) -> SimulationResult:
        isr = candidate.isr

        issues: list[SimulationIssue] = []
        logs: list[str] = []

        required_fields = ("isr_id", "version", "name")

        for field_name in required_fields:
            if not isr.get(field_name):
                issues.append(
                    SimulationIssue(
                        severity="ERROR",
                        code="ISR_MISSING_REQUIRED_FIELD",
                        message=f"ISR is missing required field: {field_name}",
                    )
                )

        services = list(iter_services(isr))
        data_models = list(iter_data_models(isr))

        service_count = len(services)

        api_count = 0
        dependency_count = 0

        dependency_graph: dict[str, list[str]] = {}

        for service in services:
            apis = service.get("apis", []) or []
            api_count += len(apis)

            dependencies = service.get("depends_on", []) or []
            dependency_count += len(dependencies)

            service_name = service.get("name")

            if service_name:
                dependency_graph[str(service_name)] = [
                    str(dependency)
                    for dependency in dependencies
                ]

        if self._has_dependency_cycle(dependency_graph):
            issues.append(
                SimulationIssue(
                    severity="ERROR",
                    code="DEPENDENCY_CYCLE",
                    message="Service dependency cycle detected.",
                )
            )

        complexity = (
            service_count
            + api_count
            + len(data_models)
            + dependency_count
        )

        metrics: dict[str, Any] = {
            "service_count": service_count,
            "api_count": api_count,
            "data_model_count": len(data_models),
            "dependency_count": dependency_count,
            "complexity": complexity,
        }

        has_error = any(issue.severity == "ERROR" for issue in issues)

        status = "FAILED" if has_error else "PASSED"

        logs.append(
            f"Simulation completed with status {status}."
        )

        simulation_id = deterministic_id(
            "simulation",
            {
                "candidate_id": candidate.id,
                "metrics": metrics,
                "issues": [issue.model_dump(mode="json") for issue in issues],
            },
        )

        return SimulationResult(
            id=simulation_id,
            candidate_id=candidate.id,
            status=status,
            metrics=metrics,
            issues=issues,
            logs=logs,
            created_at=utcnow().isoformat(),
        )

    def _has_dependency_cycle(
        self,
        graph: dict[str, list[str]],
    ) -> bool:
        WHITE = 0
        GRAY = 1
        BLACK = 2

        color: dict[str, int] = {node: WHITE for node in graph}

        def visit(node: str) -> bool:
            color[node] = GRAY

            for neighbor in graph.get(node, []):
                if neighbor not in graph:
                    continue

                if color[neighbor] == GRAY:
                    return True

                if color[neighbor] == WHITE and visit(neighbor):
                    return True

            color[node] = BLACK

            return False

        for node in graph:
            if color[node] == WHITE:
                if visit(node):
                    return True

        return False
