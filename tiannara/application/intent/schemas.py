"""Stage I/O contracts for the intent compiler.

These are the structured outputs the LanguageModelProvider must produce.
They are versioned via ``output_schema_id`` constants in ``config.py`` so
replay fixtures and schema drift are detectable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.domain.models.model_call import ModelCallRecord
from tiannara.domain.models.requirement_graph import RequirementGraph
from tiannara.domain.models.semantic_resolution import SemanticResolutionRecord
from tiannara.domain.models.system_model import SystemModel


class NormalizedIntent(BaseModel):
    original_statement: str
    normalized_statement: str
    source_statement_hash: str
    word_count: int


class AssumptionSeed(BaseModel):
    statement: str = Field(min_length=1)
    rationale: str = ""


class ElicitationOutput(BaseModel):
    inferred_capabilities: list[str] = Field(default_factory=list)
    assumptions: list[AssumptionSeed] = Field(default_factory=list)
    clarifications: list[str] = Field(default_factory=list)


class NodeSeed(BaseModel):
    ref: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    priority: str = "must"
    acceptance_criteria: list[str] = Field(default_factory=list)
    rationale: str = ""


class EdgeSeed(BaseModel):
    source_ref: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    rationale: str = ""


class ExtractionOutput(BaseModel):
    nodes: list[NodeSeed] = Field(default_factory=list)
    edges: list[EdgeSeed] = Field(default_factory=list)


class RepairOutput(ExtractionOutput):
    changes_summary: str = ""


class IntentCompilationResult(BaseModel):
    system_id: str
    isr: IntermediateSoftwareRepresentation
    requirement_graph: RequirementGraph
    call_records: list[ModelCallRecord] = Field(default_factory=list)
    repair_iterations: int = 0
    assumption_ids: list[str] = Field(default_factory=list)
    semantic_resolution_record: SemanticResolutionRecord | None = None

class TaskFlowSemanticProjection(BaseModel):
    """SystemModel plus an explicit declaration of which TaskFlow semantics it consumed.

    This declaration is a reviewable integration contract, not proof that the
    projector is correct. The projector implementation and its tests must
    demonstrate that each listed value affects the resulting model.
    """

    system_model: SystemModel
    projected_fields: tuple[str, ...]

    @model_validator(mode="after")
    def validate_projected_fields(self) -> "TaskFlowSemanticProjection":
        if len(self.projected_fields) != len(set(self.projected_fields)):
            raise ValueError("projected_fields contains duplicates")
        if any(not field.strip() for field in self.projected_fields):
            raise ValueError("projected_fields cannot contain blank paths")
        return self

    @classmethod
    def model_validate_projection(
        cls, system_model: SystemModel, projected_fields: tuple[str, ...]
    ) -> "TaskFlowSemanticProjection":
        if len(projected_fields) != len(set(projected_fields)):
            raise ValueError("projected_fields contains duplicates")
        return cls(system_model=system_model, projected_fields=projected_fields)

