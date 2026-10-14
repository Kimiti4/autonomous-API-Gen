"""Fail-closed structural binding between source bytes, requirement graph and ISR.

This verifies identity and requirement-ID traceability. It does NOT prove that
requirement statements are semantically equivalent or that generated behavior
satisfies them; those require separate semantic and runtime evidence.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from constitutional_architecture.isr.model.isr import ISR
from tiannara.domain.models.requirement_graph import RequirementGraph
from tiannara.domain.models.system_model import SystemModel


@dataclass(frozen=True)
class ConstitutionalSourceBinding:
    source_bytes: bytes
    expected_source_sha256: str
    graph: RequirementGraph
    graph_to_isr_requirement_ids: Mapping[str, str]
    system_model: SystemModel | None = None


@dataclass(frozen=True)
class ConstitutionalBindingReport:
    source_sha256: str
    graph_id: str
    graph_sha256: str
    isr_sha256: str
    bound_graph_requirement_ids: tuple[str, ...]
    unbound_mandatory_graph_requirement_ids: tuple[str, ...]
    unknown_graph_requirement_ids: tuple[str, ...]
    unknown_isr_requirement_ids: tuple[str, ...]
    duplicate_isr_requirement_ids: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not (
            self.blockers
            or self.unbound_mandatory_graph_requirement_ids
            or self.unknown_graph_requirement_ids
            or self.unknown_isr_requirement_ids
            or self.duplicate_isr_requirement_ids
        )


def verify_constitutional_source_binding(
    *, binding: ConstitutionalSourceBinding, isr: ISR
) -> ConstitutionalBindingReport:
    """Recompute source identity and require mandatory graph→ISR links."""
    source_hash = hashlib.sha256(binding.source_bytes).hexdigest()
    graph = binding.graph
    graph_hash = graph.content_hash()
    blockers: list[str] = []

    if not binding.source_bytes:
        blockers.append("source snapshot is empty")
    if source_hash != binding.expected_source_sha256:
        blockers.append("source bytes do not match the expected source SHA-256")
    provenance_hash = getattr(graph.provenance, "source_statement_hash", None)
    if provenance_hash != binding.expected_source_sha256:
        blockers.append("requirement graph provenance is not bound to the active source hash")
    if not graph.nodes:
        blockers.append("requirement graph contains no nodes")
    if not isr.system.requirements:
        blockers.append("constitutional ISR contains no requirements")
    architecture_ref = getattr(isr.system, "intent_architecture_ref", None)
    if architecture_ref is not None:
        if not architecture_ref.projection_complete:
            blockers.extend(
                f"typed architecture projection incomplete: {item}"
                for item in architecture_ref.projection_blockers
            )
        if binding.system_model is None:
            blockers.append("typed SystemModel is required to verify architecture projection")
        else:
            if binding.system_model.content_hash() != architecture_ref.system_model_sha256:
                blockers.append("typed SystemModel hash differs from the bound architecture projection")
            try:
                from constitutional_architecture.isr.semantics.intent_projection import (
                    project_intent_to_constitutional_isr,
                )
                expected_projection = project_intent_to_constitutional_isr(
                    source_bytes=binding.source_bytes,
                    graph=graph,
                    system_model=binding.system_model,
                    system_id=isr.system.id,
                )
                if expected_projection.blockers:
                    blockers.append(
                        "bound typed SystemModel cannot be completely projected: "
                        + "; ".join(expected_projection.blockers)
                    )
                if expected_projection.candidate_isr is None:
                    blockers.append("bound typed SystemModel did not produce a candidate ISR")
                elif expected_projection.candidate_isr.system.modules != isr.system.modules:
                    blockers.append("constitutional ISR modules differ from deterministic typed architecture projection")
                elif expected_projection.candidate_isr.system.security_posture != isr.system.security_posture:
                    blockers.append("constitutional ISR security posture differs from deterministic typed architecture projection")
                elif (
                    expected_projection.candidate_isr.system.infrastructure_posture,
                    expected_projection.candidate_isr.system.deployment_posture,
                    expected_projection.candidate_isr.system.testing_posture,
                    expected_projection.candidate_isr.system.documentation_posture,
                    expected_projection.candidate_isr.system.operational_posture,
                ) != (
                    isr.system.infrastructure_posture,
                    isr.system.deployment_posture,
                    isr.system.testing_posture,
                    isr.system.documentation_posture,
                    isr.system.operational_posture,
                ):
                    blockers.append("constitutional ISR policy postures differ from deterministic typed architecture projection")
            except Exception as exc:
                blockers.append(
                    f"typed architecture projection verification unavailable: "
                    f"{type(exc).__name__}: {exc}"
                )
    graph_ref = getattr(isr.system, "requirement_graph_ref", None)
    if graph_ref is not None:
        if not graph_ref.projection_complete:
            blockers.extend(
                f"intent-to-constitutional projection incomplete: {item}"
                for item in graph_ref.projection_blockers
            )
        if graph_ref.graph_id != graph.graph_id:
            blockers.append("constitutional ISR graph identity does not match the active graph")
        if graph_ref.graph_sha256 != graph_hash:
            blockers.append("constitutional ISR graph hash does not match the active graph")
        if graph_ref.source_sha256 != binding.expected_source_sha256:
            blockers.append("constitutional ISR source hash does not match the active source")
        from constitutional_architecture.isr.semantics.requirement import (
            validate_requirement_graph_projection,
        )
        projection_errors = validate_requirement_graph_projection(isr.system)
        blockers.extend(f"invalid ISR graph projection: {error}" for error in projection_errors)
        metadata_by_id = {
            item.requirement_id: item
            for item in getattr(isr.system, "requirement_source_metadata", ())
        }
        for node in graph.nodes:
            mapped_id = binding.graph_to_isr_requirement_ids.get(node.id)
            metadata = metadata_by_id.get(mapped_id) if mapped_id else None
            if metadata is None:
                blockers.append(f"graph requirement '{node.id}' has no first-class ISR source metadata")
                continue
            if (
                metadata.source_kind != node.kind.value
                or metadata.priority != node.priority.value
                or metadata.acceptance_criteria != tuple(node.acceptance_criteria)
                or metadata.verification_method != node.verification_method.value
                or metadata.rationale != node.rationale
                or metadata.provenance_source != node.provenance.source
                or metadata.taxonomy_version != node.provenance.taxonomy_version
                or metadata.stratum != node.provenance.stratum
                or metadata.seed != node.provenance.seed
                or metadata.created_by != node.provenance.created_by
            ):
                blockers.append(f"constitutional ISR metadata differs from graph requirement '{node.id}'")
        expected_relations = {
            (edge.source_id, edge.target_id, edge.kind.value, edge.rationale)
            for edge in graph.edges
        }
        actual_relations = {
            (
                relation.source_requirement_id,
                relation.target_requirement_id,
                relation.kind,
                relation.rationale,
            )
            for relation in getattr(isr.system, "requirement_relations", ())
        }
        if expected_relations != actual_relations:
            blockers.append("constitutional ISR requirement relations differ from active graph")

    graph_ids = {node.id for node in graph.nodes}
    mandatory_ids = {node.id for node in graph.nodes if node.priority.value == "must"}
    mapped_graph_ids = set(binding.graph_to_isr_requirement_ids)
    unknown_graph_ids = tuple(sorted(mapped_graph_ids - graph_ids))
    if unknown_graph_ids:
        blockers.append(f"binding references unknown graph requirements: {list(unknown_graph_ids)}")

    isr_requirement_ids = [item.requirement_id for item in isr.system.requirements]
    known_isr_ids = set(isr_requirement_ids)
    mapped_isr_ids = list(binding.graph_to_isr_requirement_ids.values())
    unknown_isr_ids = tuple(sorted(set(mapped_isr_ids) - known_isr_ids))
    if unknown_isr_ids:
        blockers.append(f"binding references unknown constitutional ISR requirements: {list(unknown_isr_ids)}")

    duplicate_isr_ids = tuple(sorted(
        item for item in set(mapped_isr_ids) if mapped_isr_ids.count(item) > 1
    ))
    if duplicate_isr_ids:
        blockers.append(f"multiple graph requirements map to the same ISR requirement: {list(duplicate_isr_ids)}")

    unbound_mandatory = tuple(sorted(mandatory_ids - mapped_graph_ids))
    if unbound_mandatory:
        blockers.append(
            "mandatory graph requirements lack constitutional ISR bindings: "
            + str(list(unbound_mandatory))
        )

    return ConstitutionalBindingReport(
        source_sha256=source_hash,
        graph_id=graph.graph_id,
        graph_sha256=graph_hash,
        isr_sha256=isr.content_hash,
        bound_graph_requirement_ids=tuple(sorted(mapped_graph_ids & graph_ids)),
        unbound_mandatory_graph_requirement_ids=unbound_mandatory,
        unknown_graph_requirement_ids=unknown_graph_ids,
        unknown_isr_requirement_ids=unknown_isr_ids,
        duplicate_isr_requirement_ids=duplicate_isr_ids,
        blockers=tuple(blockers),
    )
