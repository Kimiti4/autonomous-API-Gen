"""R2.10.7 expansion — the per-backend capability registry.

The six (plus FastAPI) capability declarations are the platform's first
honest, per-backend map of what each realization technology can and cannot
express through the frozen R2.10.6 contract. The default is honesty, not
optimism: ``declaration()`` builds exactly the twelve SEMANTIC_IDS with
UNSUPPORTED as the implicit default for anything not declared.

Every entry was source-verified against the real backend's generation
surface before being treated as authoritative:

- SUPPORTED: the backend's generation consumes the dimension's content via
  its projection seam and produces the dimension's core artifacts.
- PARTIALLY_SUPPORTED: the backend produces the dimension's artifacts but
  consumes only presence-level content, or the dimension is realized only in
  part (degradation is declared, never silent).
- UNSUPPORTED: the backend consumes none of the dimension's content through
  the projection — declaring otherwise would be aspirational, the same
  dishonesty as a silent omission with a nicer label.

Findings record the fidelity gaps and remediation notes per backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from constitutional_architecture.compilers.backend.fastapi.compiler import (
    FastAPICompiler,
)
from constitutional_architecture.compilers.database.postgres.compiler import (
    PostgresCompiler,
)
from constitutional_architecture.compilers.deployment.cicd.compiler import (
    CICDDeploymentCompiler,
)
from constitutional_architecture.compilers.documentation.markdown.compiler import (
    MarkdownDocumentationCompiler,
)
from constitutional_architecture.compilers.frontend.react.compiler import (
    ReactCompiler,
)
from constitutional_architecture.compilers.infrastructure.terraform.compiler import (
    TerraformCompiler,
)
from constitutional_architecture.compilers.testing.pytest.compiler import (
    PytestCompiler,
)

from .backend_conformance import (
    BackendCapabilityDeclaration,
    BackendConformanceAdapter,
    CapabilitySupport,
)
from .consumption_contract import CompilationTarget
from .projection_seams import (
    CicdProjectionSeam,
    MarkdownProjectionSeam,
    PostgresProjectionSeam,
    PytestProjectionSeam,
    ReactProjectionSeam,
    TerraformProjectionSeam,
)
from .backend_conformance import FastAPIProjectionSeam

SUPPORTED = CapabilitySupport.SUPPORTED
PARTIAL = CapabilitySupport.PARTIALLY_SUPPORTED
UNSUPPORTED = CapabilitySupport.UNSUPPORTED

# The twelve expressed semantics every declaration must cover (matrix
# 12 EXPRESSED): the user-specified capability vocabulary, each entry
# grouping one or more of the 14 gate-level carriers.
SEMANTIC_IDS = (
    "behavior_transitions",
    "behavior_await_surface",
    "temporal_semantics",
    "business_capabilities",
    "data_migrations",
    "reliability_resilience",
    "architecture_boundaries",
    "requirements_acceptance_traceability",
    "deployment_rollout_rollback",
    "testing_anchoring",
    "documentation",
    "evolution_objectives_protected_regions",
)


def declaration(
    backend_id: str, supported: set, partial: set
) -> BackendCapabilityDeclaration:
    """Build a declaration where anything not explicitly SUPPORTED or
    PARTIAL is UNSUPPORTED — the default is honesty, not optimism."""
    decl = {}
    for sid in SEMANTIC_IDS:
        if sid in supported:
            decl[sid] = SUPPORTED
        elif sid in partial:
            decl[sid] = PARTIAL
        else:
            decl[sid] = UNSUPPORTED
    return BackendCapabilityDeclaration(backend_id, decl)


# -- the authoritative declarations (source-verified) --------------------------

BACKEND_DECLARATIONS: Mapping[str, BackendCapabilityDeclaration] = {
    # Frontend realization: views and components surfaced from workflow
    # behavior and business capabilities. The await surface, temporal
    # semantics, requirement traceability, and documentation are NOT
    # consumable by the generated UI surface today (aspirational PARTIALs
    # would be dishonesty) — declared UNSUPPORTED with findings.
    "react": declaration(
        "react",
        supported={"behavior_transitions", "business_capabilities"},
        partial=set(),
    ),
    # Backend realization: use cases + routers from workflow behavior and
    # capabilities; reliability/boundary/deployment surfaces are realized
    # only through structural genes (consistency attributes, module
    # layering, Dockerfile) — declared PARTIAL, never SUPPORTED.
    "fastapi": declaration(
        "fastapi",
        supported={"behavior_transitions", "business_capabilities"},
        partial={
            "reliability_resilience",
            "architecture_boundaries",
            "deployment_rollout_rollback",
        },
    ),
    # Persistence realization: the migration surface (target schemas ->
    # DDL + alembic). Capabilities, reliability, and boundaries are not
    # consumable through the projection — the migration's compatibility and
    # rollback semantics are validation intents, not DDL content.
    "postgres": declaration(
        "postgres",
        supported={"data_migrations"},
        partial=set(),
    ),
    # Infrastructure realization: deployment topology artifacts exist, but
    # the generation is genome-driven — NO carrier content is consumed
    # through the projection; rollout strategy, health requirements, and
    # rollback invariants are unrealized (declared PARTIAL, never SUPPORTED).
    "terraform": declaration(
        "terraform",
        supported=set(),
        partial={"deployment_rollout_rollback"},
    ),
    # Pipeline realization: delivery stages and test execution bound to
    # carrier PRESENCE via the composed deployment bundle. The runtime
    # semantics (rollout strategy, anchor evidence, resilience policies)
    # are not its concern through the projection.
    "cicd": declaration(
        "cicd",
        supported=set(),
        partial={
            "deployment_rollout_rollback",
            "testing_anchoring",
            "reliability_resilience",
        },
    ),
    # Testing realization: test artifacts exist, but testing anchors are not
    # consumed — tests are generated, not bound to anchor evidence; the
    # entity/endpoint-driven layers realize empty defaults.
    "pytest": declaration(
        "pytest",
        supported=set(),
        partial={"testing_anchoring"},
    ),
    # Documentation realization: documentation artifacts are the backend's
    # native output. The DocumentationIntent content (purpose / audience /
    # coverage_refs) is not consumed — docs are genome-derived — and the
    # ADRs embed datetime.date.today() (latent cross-day determinism risk).
    "markdown": declaration(
        "markdown",
        supported={"documentation"},
        partial=set(),
    ),
}

BACKEND_FINDINGS: Mapping[str, tuple[str, ...]] = {
    "react": (
        "DATA_ENTITY / API_ENDPOINT / policy layers depend on structural "
        "genes (entities, endpoints, security classification) outside the "
        "14-semantic projection — realized with empty defaults today",
        "design_tokens context surface (frontend design genome) is not "
        "carried by the projection",
    ),
    "fastapi": (
        "domain-layer content depends on structural entity genes outside "
        "the 14-semantic projection (consistency attributes) — realized "
        "with defaults today",
        "Dockerfile is a realization convention, not deployment-carrier "
        "content (rollout/rollback intents unrealized)",
    ),
    "postgres": (
        "attribute / FK / policy content is structural (entity edges) — "
        "DDL realizes the migration target-schema surface only",
        "compatibility and rollback intents are validation semantics, not "
        "realized in DDL",
        "RLS is tenancy-gene driven (structural gene outside the projection)",
    ),
    "terraform": (
        "generation is genome-driven — no semantic carrier content is "
        "consumed through the projection; the deployment surface is "
        "realized from structural genes",
        "rollout strategy / health requirements / rollback invariants are "
        "unrealized (deployment_rollout_rollback declared PARTIAL, never "
        "SUPPORTED)",
        "compute generation is fallback under the default SINGLE_REGION "
        "topology",
    ),
    "cicd": (
        "presence-level consumption via the composed deployment bundle — "
        "no rollout / evidence / policy content is carried into the pipeline",
        "the bundle composition maps carrier presence only (the real "
        "meta-compiler's native input is the produced bundle, never the ISR)",
    ),
    "pytest": (
        "entity / endpoint / attribute-driven layers realize empty defaults "
        "(structural genes outside the projection)",
        "testing anchors are not consumed — tests are generated, not bound "
        "to anchor evidence (testing_anchoring declared PARTIAL, never "
        "SUPPORTED)",
        "contract tests are gated off by the default MODULAR_MONOLITH "
        "genome",
    ),
    "markdown": (
        "ERD depends on structural entity genes — empty through the "
        "projection",
        "DocumentationIntent content (purpose / audience / coverage_refs) "
        "is not consumed — docs are genome-derived",
        "ADRs embed datetime.date.today() — latent cross-day determinism "
        "risk (Gate B measures within-run determinism; remediation: inject "
        "a stable date through the seam)",
    ),
}

BACKEND_VERSIONS: Mapping[str, str] = {
    "react": "13.0.0",
    "fastapi": "8.0.0",
    "postgres": "9.0.0",
    "terraform": "10.0.0",
    "cicd": "15.0.0",
    "pytest": "11.0.0",
    "markdown": "12.0.0",
}


# -- the registry wiring (real implementations, never mocks) --------------------

@dataclass(frozen=True)
class BackendRegistration:
    backend_id: str
    real_backend: object
    version: str
    declaration: BackendCapabilityDeclaration
    projection_seam: object
    findings: tuple[str, ...]
    target: CompilationTarget


def _target(
    backend_id: str,
    language: str,
    runtime: str,
    framework: str,
    capabilities: tuple[str, ...],
) -> CompilationTarget:
    return CompilationTarget(
        target_id=f"target-{backend_id}-realization",
        language=language,
        runtime=runtime,
        framework=framework,
        capabilities=frozenset(capabilities),
        version="1.0.0",
    )


class BackendRegistry:
    """The conformance registry: per backend, the REAL implementation, its
    explicit declaration, its projection seam, its findings, and its
    realization target."""

    def __init__(self) -> None:
        self._backend_factories: dict[str, object] = {
            "react": ReactCompiler,
            "fastapi": FastAPICompiler,
            "postgres": PostgresCompiler,
            "terraform": TerraformCompiler,
            "cicd": CICDDeploymentCompiler,
            "pytest": PytestCompiler,
            "markdown": MarkdownDocumentationCompiler,
        }
        self._seams: dict[str, object] = {
            "react": ReactProjectionSeam(),
            "fastapi": FastAPIProjectionSeam(),
            "postgres": PostgresProjectionSeam(),
            "terraform": TerraformProjectionSeam(),
            "cicd": CicdProjectionSeam(),
            "pytest": PytestProjectionSeam(),
            "markdown": MarkdownProjectionSeam(),
        }
        self._targets: dict[str, CompilationTarget] = {
            "react": _target("react", "javascript", "node20", "react", ("ui",)),
            "fastapi": _target(
                "fastapi", "python", "python3.14", "fastapi", ("http-api",)
            ),
            "postgres": _target(
                "postgres", "sql", "postgres16", "postgresql", ("sql-persistence",)
            ),
            "terraform": _target(
                "terraform", "hcl", "terraform", "aws", ("infra",)
            ),
            "cicd": _target(
                "cicd", "yaml", "github-actions", "github-actions", ("pipeline",)
            ),
            "pytest": _target(
                "pytest", "python", "python3.14", "pytest", ("testing",)
            ),
            "markdown": _target(
                "markdown", "markdown", "markdown", "markdown", ("docs",)
            ),
        }

    def backend_ids(self) -> tuple[str, ...]:
        return tuple(self._backend_factories)

    def backend(self, backend_id: str) -> object:
        factory = self._backend_factories[backend_id]
        return factory()

    def version(self, backend_id: str) -> str:
        return BACKEND_VERSIONS[backend_id]

    def seam(self, backend_id: str) -> object:
        return self._seams[backend_id]

    def target(self, backend_id: str) -> CompilationTarget:
        return self._targets[backend_id]

    def adapter(self, backend_id: str) -> BackendConformanceAdapter:
        return BackendConformanceAdapter(
            backend_id=backend_id,
            backend_version=self.version(backend_id),
            real_backend=self.backend(backend_id),
            declaration=BACKEND_DECLARATIONS[backend_id],
            projection_seam=self.seam(backend_id),
            findings=BACKEND_FINDINGS[backend_id],
        )


def conform_all_backends(
    isr: object, registry: BackendRegistry, evaluator: object
) -> dict[str, object]:
    """Conform every registered backend to the frozen contract and
    chain-anchor each report on the evidence ledger."""
    reports = {}
    for backend_id in registry.backend_ids():
        adapter = registry.adapter(backend_id)
        report = evaluator.conform(adapter, isr, registry.target(backend_id))
        evaluator.record_report(report)
        reports[backend_id] = report
    return reports