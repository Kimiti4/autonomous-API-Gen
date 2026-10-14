"""Loss-aware projection from the intent graph into constitutional ISR semantics.

The adapter deliberately separates a candidate projection from authorization to
compile it. Requirement graph identity, node metadata, and graph relations are
projected into first-class ISR records. Typed architectural fields not yet
translated into constitutional genes are reported as blockers; a candidate
with blockers must never be passed to source-bound compilation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System, SystemMetadata
from constitutional_architecture.isr.semantics.capability import BusinessCapability
from constitutional_architecture.isr.semantics.requirement import (
    Requirement,
    RequirementGraphReference,
    RequirementRelation,
    RequirementSourceMetadata,
)
from tiannara.domain.models.requirement_graph import RequirementGraph
from tiannara.domain.models.system_model import SystemModel


@dataclass(frozen=True)
class IntentProjectionResult:
    candidate_isr: ISR | None
    source_sha256: str
    graph_sha256: str
    system_model_sha256: str
    requirement_id_map: tuple[tuple[str, str], ...]
    blockers: tuple[str, ...]

    @property
    def ready_for_compilation(self) -> bool:
        return self.candidate_isr is not None and not self.blockers


def _stable_capability_id(requirement_id: str) -> str:
    digest = hashlib.sha256(requirement_id.encode("utf-8")).hexdigest()[:16]
    return f"cap-req-{digest}"


def project_intent_to_constitutional_isr(
    *,
    source_bytes: bytes,
    graph: RequirementGraph,
    system_model: SystemModel,
    system_id: str,
) -> IntentProjectionResult:
    """Create a traceable candidate ISR, refusing unverified/lossy projections.

    All graph nodes, priorities, acceptance text, verification methods,
    rationale, provenance, and edges are preserved in first-class records.
    This initial adapter does not yet lower the typed SystemModel's service,
    component, API, event, data, security, deployment, testing, or operations
    sections to constitutional genes; any non-empty such section is a blocker.
    """
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    graph_hash = graph.content_hash()
    model_hash = system_model.content_hash()
    blockers: list[str] = []

    if not source_bytes:
        blockers.append("source snapshot is empty")
    if graph.provenance.source_statement_hash != source_hash:
        blockers.append("graph provenance does not match exact source bytes")
    if system_model.requirements_ref.graph_id != graph.graph_id:
        blockers.append("SystemModel references a different requirement graph ID")
    if system_model.requirements_ref.graph_hash != graph_hash:
        blockers.append("SystemModel references a stale requirement graph hash")
    if not graph.nodes:
        blockers.append("requirement graph has no nodes")

    nodes = {node.id: node for node in graph.nodes}
    capabilities: list[BusinessCapability] = []
    requirements: list[Requirement] = []
    metadata: list[RequirementSourceMetadata] = []
    id_map: list[tuple[str, str]] = []

    for node in graph.nodes:
        cap_id = _stable_capability_id(node.id)
        capabilities.append(
            BusinessCapability(
                capability_id=cap_id,
                intent=node.statement,
                requirement_refs=(node.id,),
            )
        )
        acceptance_text = tuple(node.acceptance_criteria)
        requirements.append(
            Requirement(
                requirement_id=node.id,
                statement=node.statement,
                target_refs=(cap_id,),
            )
        )
        metadata.append(
            RequirementSourceMetadata(
                requirement_id=node.id,
                source_kind=node.kind.value,
                priority=node.priority.value,
                acceptance_criteria=acceptance_text,
                verification_method=node.verification_method.value,
                rationale=node.rationale,
                provenance_source=node.provenance.source,
                taxonomy_version=node.provenance.taxonomy_version,
                stratum=node.provenance.stratum,
                seed=node.provenance.seed,
                created_by=node.provenance.created_by,
            )
        )
        id_map.append((node.id, node.id))

    relations = tuple(
        RequirementRelation(
            source_requirement_id=edge.source_id,
            target_requirement_id=edge.target_id,
            kind=edge.kind.value,
            rationale=edge.rationale,
        )
        for edge in graph.edges
    )

    # The typed SystemModel is an independent architecture projection. Do not
    # imply that requirement preservation means its architecture was preserved.
    architecture_sections = {
        "domains": system_model.domains,
        "services": system_model.services,
        "components": system_model.components,
        "apis": system_model.apis,
        "events": system_model.events,
        "data_models": system_model.data_models,
    }
    for section, values in architecture_sections.items():
        if values:
            blockers.append(
                f"typed SystemModel section '{section}' has {len(values)} item(s) "
                "not yet lowered to constitutional architecture genes"
            )
    if system_model.security.model_dump(exclude_defaults=True):
        blockers.append("typed SystemModel security posture is not yet lowered")
    if system_model.infrastructure.model_dump(exclude_defaults=True):
        blockers.append("typed SystemModel infrastructure is not yet lowered")
    if system_model.deployment.model_dump(exclude_defaults=True):
        blockers.append("typed SystemModel deployment policy is not yet lowered")
    if system_model.testing.model_dump(exclude_defaults=True):
        blockers.append("typed SystemModel testing policy is not yet lowered")
    if system_model.documentation.model_dump(exclude_defaults=True):
        blockers.append("typed SystemModel documentation policy is not yet lowered")
    if system_model.operational_policies.model_dump(exclude_defaults=True):
        blockers.append("typed SystemModel operational policies are not yet lowered")
    if system_model.extensions:
        blockers.append("typed SystemModel contains extensions with no declared lowering")

    # Detect accidental dangling relations even though RequirementGraph itself
    # validates this invariant at construction; retain the check at the boundary.
    for edge in graph.edges:
        if edge.source_id not in nodes or edge.target_id not in nodes:
            blockers.append(
                f"relation {edge.source_id}->{edge.target_id} references an unknown node"
            )

    candidate = ISR(
        system=System(
            id=system_id,
            name=system_model.system_name,
            description=system_model.problem_statement,
            metadata=SystemMetadata(description=system_model.problem_statement),
            business_capabilities=tuple(capabilities),
            requirements=tuple(requirements),
            requirement_graph_ref=RequirementGraphReference(
                graph_id=graph.graph_id,
                graph_sha256=graph_hash,
                source_sha256=source_hash,
            ),
            requirement_source_metadata=tuple(metadata),
            requirement_relations=relations,
        )
    ) if not any(
        blocker in {
            "source snapshot is empty",
            "graph provenance does not match exact source bytes",
            "SystemModel references a different requirement graph ID",
            "SystemModel references a stale requirement graph hash",
            "requirement graph has no nodes",
        }
        for blocker in blockers
    ) else None

    return IntentProjectionResult(
        candidate_isr=candidate,
        source_sha256=source_hash,
        graph_sha256=graph_hash,
        system_model_sha256=model_hash,
        requirement_id_map=tuple(id_map),
        blockers=tuple(blockers),
    )
