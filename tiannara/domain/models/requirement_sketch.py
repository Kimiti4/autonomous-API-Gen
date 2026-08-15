"""RequirementSketch -- structured ground truth for synthesized projects.

A sketch is the requirement structure a stratum instance is *intended* to
express. Capability B4 renders sketches into messy natural language;
Capability B3's Intent Compiler must reconstruct the structure; the diff is
the extraction-fidelity metric. Sketches never leave the harness side --
rendered statements carry no sketch content.

Determinism contract: identical (taxonomy_version, seed, instance_index)
produces byte-identical sketches and hashes.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field

from ..services.canonical import canonical_hash
from .requirement_graph import RequirementKind
from .system_model import Priority


class PlantedDefectKind(str, enum.Enum):
    CONTRADICTION = "contradiction"
    MISSING_MUST = "missing_must"
    AMBIGUITY = "ambiguity"


class PlantedDefect(BaseModel):
    kind: PlantedDefectKind
    target_ref: str
    description: str


class ExpectedRequirement(BaseModel):
    ref_id: str
    kind: RequirementKind
    priority: Priority
    topic: str


class StratumAssignment(BaseModel):
    domain: str
    complexity_tier: str
    capability_class: str
    scale_tier: str
    integration_pattern: str
    compliance_regime: str

    def key(self) -> str:
        return "|".join(
            (
                self.domain,
                self.complexity_tier,
                self.capability_class,
                self.scale_tier,
                self.integration_pattern,
                self.compliance_regime,
            )
        )


class SketchProvenance(BaseModel):
    taxonomy_version: str
    stratum: StratumAssignment
    seed: int
    instance_index: int
    epoch: int = 0


class ComplexityBudget(BaseModel):
    expected_services: int
    expected_requirements_range: tuple[int, int]
    throughput_class: str
    availability_posture: str


class RequirementSketch(BaseModel):
    sketch_id: str
    provenance: SketchProvenance
    assignment: StratumAssignment
    expected_capabilities: list[str] = Field(default_factory=list)
    expected_data_entities: list[str] = Field(default_factory=list)
    expected_requirements: list[ExpectedRequirement] = Field(default_factory=list)
    planted_defects: list[PlantedDefect] = Field(default_factory=list)
    budget: ComplexityBudget

    def content_hash(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))

    def requirement_refs(self) -> list[str]:
        return [requirement.ref_id for requirement in self.expected_requirements]
