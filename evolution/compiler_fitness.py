"""
Compiler-in-the-loop fitness evaluation.

This module evaluates candidate ISR architectures by compiling them through
compiler backends and converting compilation evidence into fitness objectives
and constraints.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from .models import CandidateArchitecture, FitnessEvaluation, utcnow
from .utils import deterministic_id


class BackendCompilationResult(BaseModel):
    """Result of compiling a candidate ISR with one backend."""

    backend_id: str

    status: str = "FAILED"

    artifact_count: int = 0
    total_bytes: int = 0

    artifact_paths: list[str] = Field(default_factory=list)

    issues: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)


class CompilationFitnessReport(BaseModel):
    """Fitness report produced from compiler-in-the-loop evaluation."""

    candidate_id: str

    results: list[BackendCompilationResult] = Field(default_factory=list)

    objectives: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, bool] = Field(default_factory=dict)

    passed: bool = False

    issues: list[str] = Field(default_factory=list)

    created_at: str


class CompilerFitnessPolicy(BaseModel):
    """Policy controlling compiler-in-the-loop fitness evaluation."""

    backend_ids: list[str] = Field(default_factory=list)
    required_backend_ids: list[str] = Field(default_factory=list)

    environment: str = "development"

    expected_artifacts_per_backend: int = Field(default=3, ge=1)

    min_objective_value: float = Field(default=0.2, ge=0.0, le=1.0)

    required_objectives: list[str] = Field(
        default_factory=lambda: [
            "compilability",
        ]
    )

    require_docker: bool = False
    require_tests: bool = False
    require_openapi: bool = False
    require_migrations: bool = False
    require_ci: bool = False


class CompilerGateway(Protocol):
    """Abstract gateway to the Universal Compiler."""

    def compile_backend(
        self,
        isr: dict[str, Any],
        backend_id: str,
        environment: str,
    ) -> BackendCompilationResult:
        ...


class StaticCompilerGateway:
    """Static compiler gateway useful for tests and local development."""

    def __init__(
        self,
        results_by_backend: dict[str, BackendCompilationResult],
        default_result: BackendCompilationResult | None = None,
    ) -> None:
        self._results_by_backend = results_by_backend
        self._default_result = default_result

    def compile_backend(
        self,
        isr: dict[str, Any],
        backend_id: str,
        environment: str,
    ) -> BackendCompilationResult:
        result = self._results_by_backend.get(backend_id)

        if result:
            return result.model_copy(
                update={
                    "backend_id": backend_id,
                }
            )

        if self._default_result:
            return self._default_result.model_copy(
                update={
                    "backend_id": backend_id,
                }
            )

        return BackendCompilationResult(
            backend_id=backend_id,
            status="FAILED",
            issues=[
                f"No static compilation result configured for backend {backend_id}."
            ],
        )


class InProcessCompilerGateway:
    """
    Gateway that calls an in-process Universal Compiler instance.

    The compiler may be a plain UniversalCompiler or a GovernedCompiler.
    """

    def __init__(self, compiler: Any) -> None:
        self._compiler = compiler

    def compile_backend(
        self,
        isr: dict[str, Any],
        backend_id: str,
        environment: str,
    ) -> BackendCompilationResult:
        try:
            from compiler.models import CompilationRequest, CompilationTarget
        except Exception as exc:
            return BackendCompilationResult(
                backend_id=backend_id,
                status="FAILED",
                issues=[
                    f"Compiler models unavailable: {exc}",
                ],
            )

        request = CompilationRequest(
            isr=isr,
            target=CompilationTarget(
                backend_id=backend_id,
            ),
            environment=environment,
        )

        try:
            result = self._compiler.compile(request)
        except Exception as exc:
            return BackendCompilationResult(
                backend_id=backend_id,
                status="FAILED",
                issues=[
                    str(exc),
                ],
            )

        if getattr(result, "status", "FAILED") != "SUCCEEDED":
            return BackendCompilationResult(
                backend_id=backend_id,
                status="FAILED",
                issues=[
                    result.error or "Compilation failed.",
                ],
                logs=getattr(result, "logs", []),
            )

        manifest = getattr(result, "artifact_manifest", None)

        if not manifest:
            return BackendCompilationResult(
                backend_id=backend_id,
                status="FAILED",
                issues=[
                    "Compilation succeeded but no artifact manifest was produced.",
                ],
                logs=getattr(result, "logs", []),
            )

        files = getattr(manifest, "files", [])

        artifact_paths = [
            getattr(file, "path", "")
            for file in files
        ]

        total_bytes = sum(
            int(getattr(file, "size_bytes", 0))
            for file in files
        )

        return BackendCompilationResult(
            backend_id=backend_id,
            status="SUCCEEDED",
            artifact_count=len(files),
            total_bytes=total_bytes,
            artifact_paths=artifact_paths,
            logs=getattr(result, "logs", []),
        )


class CompilerFitnessEvaluator:
    """Evaluates candidate architectures using compiler backends."""

    def __init__(
        self,
        gateway: CompilerGateway,
        policy: CompilerFitnessPolicy,
    ) -> None:
        self.gateway = gateway
        self.policy = policy

    def evaluate_candidate(
        self,
        candidate: CandidateArchitecture,
    ) -> CompilationFitnessReport:
        requested_backend_ids = (
            self.policy.backend_ids
            or self.policy.required_backend_ids
        )

        if not requested_backend_ids:
            return CompilationFitnessReport(
                candidate_id=candidate.id,
                results=[],
                objectives={},
                constraints={
                    "compiler_configuration_valid": False,
                },
                passed=False,
                issues=[
                    "Compiler fitness policy does not define any backend IDs.",
                ],
                created_at=utcnow().isoformat(),
            )

        required_backend_ids = (
            self.policy.required_backend_ids
            or requested_backend_ids
        )

        results: list[BackendCompilationResult] = []

        for backend_id in requested_backend_ids:
            result = self.gateway.compile_backend(
                candidate.isr,
                backend_id,
                self.policy.environment,
            )

            results.append(result)

        requested_set = set(requested_backend_ids)
        required_set = set(required_backend_ids)

        success_results = [
            result
            for result in results
            if result.status == "SUCCEEDED"
        ]

        required_success_results = [
            result
            for result in success_results
            if result.backend_id in required_set
        ]

        success_count = len(success_results)
        required_success_count = len(required_success_results)

        compilability = (
            required_success_count / len(required_set)
            if required_set
            else 0.0
        )

        backend_coverage = (
            success_count / len(requested_set)
            if requested_set
            else 0.0
        )

        total_artifacts = sum(
            result.artifact_count
            for result in results
        )

        expected_artifacts = max(
            1,
            len(requested_backend_ids)
            * self.policy.expected_artifacts_per_backend,
        )

        artifact_completeness = min(
            1.0,
            total_artifacts / expected_artifacts,
        )

        artifact_paths = {
            path
            for result in results
            for path in result.artifact_paths
        }

        deployability = 1.0 if self._has_evidence(
            artifact_paths,
            [
                "Dockerfile",
                "docker-compose",
                "compose.yml",
                "compose.yaml",
            ],
        ) else 0.0

        test_evidence = 1.0 if self._has_evidence(
            artifact_paths,
            [
                "tests/",
                "test_",
                ".test.",
                "spec.",
            ],
        ) else 0.0

        contract_evidence = 1.0 if self._has_evidence(
            artifact_paths,
            [
                "openapi",
                "swagger",
                "docs/api",
            ],
        ) else 0.0

        persistence_evidence = 1.0 if self._has_evidence(
            artifact_paths,
            [
                "migrations/",
                ".sql",
            ],
        ) else 0.0

        ci_evidence = 1.0 if self._has_evidence(
            artifact_paths,
            [
                ".github/workflows",
                "ci.yml",
                ".gitlab-ci",
                "Jenkinsfile",
            ],
        ) else 0.0

        objectives = {
            "compilability": round(compilability, 4),
            "backend_coverage": round(backend_coverage, 4),
            "artifact_completeness": round(artifact_completeness, 4),
            "deployability": round(deployability, 4),
            "test_evidence": round(test_evidence, 4),
            "contract_evidence": round(contract_evidence, 4),
            "persistence_evidence": round(persistence_evidence, 4),
            "ci_evidence": round(ci_evidence, 4),
        }

        constraints = {
            "compiler_configuration_valid": True,
            "all_required_backends_succeeded": (
                required_success_count == len(required_set)
            ),
            "artifact_manifests_present": all(
                result.artifact_count > 0
                for result in success_results
            ),
        }

        if self.policy.require_docker:
            constraints["docker_evidence_present"] = deployability > 0.0

        if self.policy.require_tests:
            constraints["test_evidence_present"] = test_evidence > 0.0

        if self.policy.require_openapi:
            constraints["contract_evidence_present"] = contract_evidence > 0.0

        if self.policy.require_migrations:
            constraints["persistence_evidence_present"] = persistence_evidence > 0.0

        if self.policy.require_ci:
            constraints["ci_evidence_present"] = ci_evidence > 0.0

        issues: list[str] = []

        for result in results:
            if result.status != "SUCCEEDED":
                issues.append(
                    f"Backend {result.backend_id} failed: "
                    + "; ".join(result.issues)
                )

        required_objective_passed = all(
            objectives.get(objective_name, 0.0) >= self.policy.min_objective_value
            for objective_name in self.policy.required_objectives
            if objective_name in objectives
        )

        passed = all(constraints.values()) and required_objective_passed

        return CompilationFitnessReport(
            candidate_id=candidate.id,
            results=results,
            objectives=objectives,
            constraints=constraints,
            passed=passed,
            issues=issues,
            created_at=utcnow().isoformat(),
        )

    def _has_evidence(
        self,
        artifact_paths: set[str],
        markers: list[str],
    ) -> bool:
        normalized_paths = {
            path.lower()
            for path in artifact_paths
        }

        return any(
            marker.lower() in path
            for path in normalized_paths
            for marker in markers
        )


def merge_fitness(
    base_fitness: FitnessEvaluation,
    compilation_report: CompilationFitnessReport,
    candidate_id: str,
) -> FitnessEvaluation:
    """Merge base architectural fitness with compiler fitness evidence."""

    objectives = dict(base_fitness.objectives)
    constraints = dict(base_fitness.constraints)

    for objective_name, objective_value in compilation_report.objectives.items():
        objectives[f"compiler_{objective_name}"] = objective_value

    for constraint_name, constraint_value in compilation_report.constraints.items():
        constraints[f"compiler_{constraint_name}"] = constraint_value

    notes = list(base_fitness.notes)

    if not compilation_report.passed:
        notes.append("Compiler-in-the-loop fitness failed.")

    notes.extend(compilation_report.issues[:5])

    passed = base_fitness.passed and compilation_report.passed

    fitness_id = deterministic_id(
        "compiler_aware_fitness",
        {
            "candidate_id": candidate_id,
            "objectives": objectives,
            "constraints": constraints,
        },
    )

    return FitnessEvaluation(
        id=fitness_id,
        candidate_id=candidate_id,
        objectives=objectives,
        constraints=constraints,
        passed=passed,
        notes=notes,
        created_at=utcnow().isoformat(),
    )
