"""R2.10.7 expansion — backend-specific, projection-only seams.

Each seam translates the BackendSemanticModel into the real backend's
universal inputs. PROJECTION-ONLY discipline: the seam never reaches into
the semantic ISR object graph — every node, gene, context value, and bundle
entry is derived from the model's canonical constraints.

The seams are the honest map of what each realization technology can
consume through the contract. Where a real backend's generation depends on
structural genes that the 14-semantic projection does not carry (entities,
interfaces, design tokens, genome genes), the seam delivers the projection's
content faithfully and leaves the rest to defaults — the gap is recorded as
a conformance finding, never invented away.

Verification notes (source-audited per backend, recorded in the registry):

- React consumes FRONTEND_VIEW / SERVICE / COMPONENT / DATA_ENTITY /
  API_ENDPOINT nodes and context design tokens. The seam delivers
  views+services from behaviors and components from capabilities; the
  entity/endpoint/policy layers realize empty defaults (structural gap).
- Postgres consumes DATA_ENTITY nodes + attribute/FK/policy edges. The seam
  derives DATA_ENTITY nodes from migration target_schema_refs; attribute
  structure is outside the projection (structural gap).
- Terraform consumes genome genes + context only — no carrier content is
  consumable through the projection (its generation is structural-gene
  driven; recorded as a finding).
- CI/CD is a meta-compiler: it consumes a SystemDeploymentBundle. The seam
  composes the bundle from carrier PRESENCE (behaviors -> backend bundle,
  migrations -> database bundle, deployment -> infra bundle, testing
  anchors -> tests bundle, reliability -> operations bundle).
- Pytest consumes DATA_ENTITY / API_ENDPOINT / SERVICE / DATA_ATTRIBUTE
  nodes; contract tests are gated by the app_arch gene (default
  MODULAR_MONOLITH). The seam delivers services from behaviors; the
  entity/endpoint layers realize empty defaults (structural gap).
- Markdown consumes DATA_ENTITY nodes, genome genes, and intent. The seam
  delivers the projection; the ERD depends on structural entity genes
  (empty) and the ADRs embed datetime.date.today() (latent cross-day
  determinism risk, recorded as a finding).
"""
from __future__ import annotations

from typing import Any, Dict

from constitutional_architecture.core.models.bundle import (
    CompilationBundle,
    SystemDeploymentBundle,
)
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.isr import (
    ISRNode,
    NodeType,
    UniversalISR,
)

from .backend_conformance import ProjectionSeam, UniversalInputs
from .consumption_contract import BackendSemanticModel


def _behavior_services(model: BackendSemanticModel) -> list[ISRNode]:
    """Behaviors (workflows) -> SERVICE nodes — the shared projection for
    every backend that consumes services."""
    nodes: list[ISRNode] = []
    for kind, form in model.constraints:
        if kind == "behavior":
            workflow_id = str(form.get("id") or "unknown")
            nodes.append(
                ISRNode(
                    id=f"svc_{workflow_id}",
                    type=NodeType.SERVICE,
                    semantic_attributes={
                        "capability": str(form.get("name") or workflow_id),
                        "behavior_id": workflow_id,
                    },
                )
            )
    return nodes


def _capability_components(model: BackendSemanticModel) -> list[ISRNode]:
    """Capabilities -> COMPONENT nodes (the UI realization surface)."""
    nodes: list[ISRNode] = []
    for kind, form in model.constraints:
        if kind == "capability":
            capability_id = str(form.get("capability_id") or "unknown")
            nodes.append(
                ISRNode(
                    id=f"comp_{capability_id}",
                    type=NodeType.COMPONENT,
                    semantic_attributes={
                        "capability": str(form.get("intent") or capability_id)
                    },
                )
            )
    return nodes


def _migration_entities(model: BackendSemanticModel) -> list[ISRNode]:
    """Data migrations -> DATA_ENTITY nodes derived from the migration's
    target_schema_ref — the schema the migration evolves to. A migration is
    translated onto the data surface it targets, never reinterpreted."""
    nodes: list[ISRNode] = []
    for kind, form in model.constraints:
        if kind == "migration":
            target = str(form.get("target_schema_ref") or "unknown")
            safe = target.replace(":", "_").replace("/", "_")
            nodes.append(
                ISRNode(
                    id=f"entity_{safe}",
                    type=NodeType.DATA_ENTITY,
                    semantic_attributes={
                        "name": safe,
                        "migration_id": str(form.get("migration_id") or "unknown"),
                    },
                )
            )
    return nodes


def _has_carrier(model: BackendSemanticModel, kind: str) -> bool:
    return any(constraint_kind == kind for constraint_kind, _ in model.constraints)


class ReactProjectionSeam(ProjectionSeam):
    """behaviors -> FRONTEND_VIEW + SERVICE, capabilities -> COMPONENT."""

    def translate(self, model: BackendSemanticModel) -> UniversalInputs:
        nodes: dict[str, ISRNode] = {}
        for svc in _behavior_services(model):
            nodes[svc.id] = svc
            leaf = svc.id[len("svc_"):]
            nodes[f"fe_{leaf}"] = ISRNode(
                id=f"fe_{leaf}",
                type=NodeType.FRONTEND_VIEW,
                semantic_attributes={
                    "capability": svc.semantic_attributes["capability"]
                },
            )
        for comp in _capability_components(model):
            nodes[comp.id] = comp
        return UniversalInputs(
            universal_isr=UniversalISR(nodes=nodes, edges=[]),
            genome=ArchitectureGenome(),
            context={},
        )


class PostgresProjectionSeam(ProjectionSeam):
    """data_migrations -> DATA_ENTITY (the migration's target schema)."""

    def translate(self, model: BackendSemanticModel) -> UniversalInputs:
        nodes = {node.id: node for node in _migration_entities(model)}
        return UniversalInputs(
            universal_isr=UniversalISR(nodes=nodes, edges=[]),
            genome=ArchitectureGenome(),
            context={},
        )


class TerraformProjectionSeam(ProjectionSeam):
    """No carrier content is consumable by the real backend (genome/context
    only) — the seam delivers an empty graph and default genome, and the
    honest declaration + findings carry the rest."""

    def translate(self, model: BackendSemanticModel) -> UniversalInputs:
        return UniversalInputs(
            universal_isr=UniversalISR(nodes={}, edges=[]),
            genome=ArchitectureGenome(),
            context={},
        )


def _bundle_entry(
    compiler_id: str, target_technology: str, interfaces: Dict[str, Any]
) -> CompilationBundle:
    return CompilationBundle(
        compiler_id=compiler_id,
        target_technology=target_technology,
        manifests=[],
        exposed_interfaces=interfaces,
    )


class CicdProjectionSeam(ProjectionSeam):
    """Carrier PRESENCE -> SystemDeploymentBundle entries (the meta-compiler's
    native input): behaviors -> backend bundle, migrations -> database bundle,
    deployment -> infra bundle, testing anchors -> tests bundle, reliability
    -> operations bundle. Presence-level only — the bundle carries no
    semantic content, which the findings record."""

    def translate(self, model: BackendSemanticModel) -> UniversalInputs:
        bundles: Dict[str, CompilationBundle] = {}
        if _has_carrier(model, "behavior"):
            bundles["fastapi_hexagonal"] = _bundle_entry(
                "fastapi_hexagonal", "python_fastapi", {"backend_port": 8000}
            )
        if _has_carrier(model, "migration"):
            bundles["postgres_alembic"] = _bundle_entry(
                "postgres_alembic", "postgresql", {}
            )
        if _has_carrier(model, "deployment"):
            bundles["terraform_aws"] = _bundle_entry(
                "terraform_aws",
                "terraform",
                {"deployment_cmd": "terraform apply -auto-approve"},
            )
        if _has_carrier(model, "testing_anchor"):
            bundles["pytest_layered"] = _bundle_entry(
                "pytest_layered", "pytest", {}
            )
        if _has_carrier(model, "reliability"):
            bundles["operational_intelligence_v1"] = _bundle_entry(
                "operational_intelligence_v1",
                "operational",
                {"prometheus_port": 9090, "grafana_port": 3001},
            )
        return UniversalInputs(
            universal_isr=UniversalISR(nodes={}, edges=[]),
            genome=ArchitectureGenome(),
            context={},
            system_bundle=SystemDeploymentBundle(
                project_name="generated-system", bundles=bundles
            ),
        )


class PytestProjectionSeam(ProjectionSeam):
    """behaviors -> SERVICE nodes (the shared service projection); the
    entity/endpoint-driven layers realize empty defaults (structural gap)."""

    def translate(self, model: BackendSemanticModel) -> UniversalInputs:
        nodes = {node.id: node for node in _behavior_services(model)}
        return UniversalInputs(
            universal_isr=UniversalISR(nodes=nodes, edges=[]),
            genome=ArchitectureGenome(),
            context={},
        )


class MarkdownProjectionSeam(ProjectionSeam):
    """The projection carries no entity/interfaces — the ERD realizes empty
    defaults; README/ADRs derive from the default genome."""

    def translate(self, model: BackendSemanticModel) -> UniversalInputs:
        return UniversalInputs(
            universal_isr=UniversalISR(nodes={}, edges=[]),
            genome=ArchitectureGenome(),
            context={},
        )