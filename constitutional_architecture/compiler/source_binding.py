"""Fail-closed binding contract for source graphs and the constitutional ISR.

This is a structural integrity gate, not a semantic satisfaction proof. It
binds exact source bytes, the canonical requirement graph, and ISR requirement
identities before the constitutional compiler may proceed when the gate is
required by configuration.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from constitutional_architecture.isr.model.isr import ISR
from tiannara.domain.models.requirement_graph import RequirementGraph


@dataclass(frozen=True)
class ConstitutionalSourceBinding:
    source_bytes: bytes
    expected_source_sha256: str
    graph: RequirementGraph
    graph_to_isr_requirement_ids: Mapping[str, str]


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
    """Recompute source identity and require exact mandatory graph→ISR links."""
    source_hash = hashlib.sha256(binding.source_bytes).hexdigest()
    graph = binding.graph
    graph_hash = graph.content_hash()
    blockers: list[str] = []

    if source_hash != binding.expected_source_sha256:
        blockers.append("source bytes do not match the expected source SHA-256")
    provenance_hash = getattr(graph.provenance, "source_statement_hash", None)
    if provenance_hash != binding.expected_source_sha256:
        blockers.append("requirement graph provenance is not bound to the active source hash")

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
