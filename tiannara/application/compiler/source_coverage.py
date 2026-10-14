"""Explicit source-unit coverage contracts for source-to-graph fidelity.

This module verifies completeness and integrity of an independently produced
source map. It does not decide whether a mapping is semantically correct;
that requires parser/extractor provenance and adversarial review. Missing
mappings are blockers, never inferred from graph hashes.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tiannara.domain.models.requirement_graph import RequirementGraph


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SourceUnit(BaseModel):
    """A requirement-bearing byte span in the exact source snapshot."""
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    unit_id: str = Field(min_length=1, max_length=256)
    start_byte: int = Field(ge=0)
    end_byte: int = Field(gt=0)
    unit_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_range(self) -> "SourceUnit":
        if self.end_byte <= self.start_byte:
            raise ValueError("source unit end_byte must be greater than start_byte")
        return self


class SourceUnitBinding(BaseModel):
    """Maps one source unit to one or more graph node IDs."""
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    unit_id: str = Field(min_length=1, max_length=256)
    graph_node_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_node_ids(self) -> "SourceUnitBinding":
        if any(not item.strip() for item in self.graph_node_ids):
            raise ValueError("graph_node_ids cannot contain blank values")
        if len(set(self.graph_node_ids)) != len(self.graph_node_ids):
            raise ValueError("graph_node_ids cannot contain duplicates")
        return self


@dataclass(frozen=True)
class SourceGraphCoverageReport:
    source_sha256: str
    graph_sha256: str
    covered_unit_ids: tuple[str, ...]
    uncovered_unit_ids: tuple[str, ...]
    unbound_required_node_ids: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not self.blockers and not self.uncovered_unit_ids and not self.unbound_required_node_ids


def verify_source_graph_coverage(
    *,
    source_bytes: bytes,
    expected_source_sha256: str,
    graph: RequirementGraph,
    units: Iterable[SourceUnit],
    bindings: Iterable[SourceUnitBinding],
) -> SourceGraphCoverageReport:
    """Verify byte-span integrity and total declared source-unit/node coverage.

    The units inventory must come from a trusted parser or reviewer that
    identifies every requirement-bearing source unit. This function cannot
    prove that inventory semantically complete or that a mapping preserves
    meaning; it makes omissions explicit and testable instead of assuming a
    graph hash proves fidelity.
    """
    blockers: list[str] = []
    actual_source_sha256 = _sha256(source_bytes)
    if actual_source_sha256 != expected_source_sha256:
        blockers.append("source snapshot hash does not match active source bytes")

    unit_list = tuple(units)
    binding_list = tuple(bindings)
    unit_ids = [unit.unit_id for unit in unit_list]
    if len(unit_ids) != len(set(unit_ids)):
        blockers.append("duplicate source unit IDs")
    binding_ids = [binding.unit_id for binding in binding_list]
    if len(binding_ids) != len(set(binding_ids)):
        blockers.append("duplicate source unit bindings")

    source_node_ids = {node.id for node in graph.nodes}
    unit_by_id = {unit.unit_id: unit for unit in unit_list}
    binding_by_id = {binding.unit_id: binding for binding in binding_list}

    previous_end = -1
    for unit in sorted(unit_list, key=lambda item: (item.start_byte, item.end_byte)):
        if unit.end_byte > len(source_bytes):
            blockers.append(f"source unit range exceeds snapshot: {unit.unit_id}")
            continue
        if unit.start_byte < previous_end:
            blockers.append(f"overlapping source unit range: {unit.unit_id}")
        previous_end = max(previous_end, unit.end_byte)
        span = source_bytes[unit.start_byte:unit.end_byte]
        if not span.strip():
            blockers.append(f"source unit is empty or whitespace: {unit.unit_id}")
        if _sha256(span) != unit.unit_sha256:
            blockers.append(f"source unit hash mismatch: {unit.unit_id}")

    unknown_binding_units = sorted(set(binding_by_id) - set(unit_by_id))
    if unknown_binding_units:
        blockers.append(f"bindings reference unknown source units: {unknown_binding_units}")

    covered: set[str] = set()
    node_coverage: set[str] = set()
    for unit_id, binding in binding_by_id.items():
        if unit_id not in unit_by_id:
            continue
        covered.add(unit_id)
        for node_id in binding.graph_node_ids:
            if node_id not in source_node_ids:
                blockers.append(f"source unit {unit_id} maps to unknown graph node: {node_id}")
            else:
                node_coverage.add(node_id)

    uncovered = tuple(sorted(set(unit_by_id) - covered))
    if uncovered:
        blockers.append(f"requirement-bearing source units lack graph mappings: {list(uncovered)}")

    required_nodes = {node.id for node in graph.nodes if node.priority.value == "must"}
    unbound_required = tuple(sorted(required_nodes - node_coverage))
    if unbound_required:
        blockers.append(f"mandatory graph nodes lack source-unit mappings: {list(unbound_required)}")

    return SourceGraphCoverageReport(
        source_sha256=actual_source_sha256,
        graph_sha256=graph.content_hash(),
        covered_unit_ids=tuple(sorted(covered)),
        uncovered_unit_ids=uncovered,
        unbound_required_node_ids=unbound_required,
        blockers=tuple(blockers),
    )
