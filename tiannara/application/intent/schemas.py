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
from tiannara.domain.models.authorization_semantic_obligations import AuthorizationSemanticObligations
from tiannara.domain.models.system_model import SystemModel
from tiannara.application.compiler.source_projection import SourceProjectionContext
from tiannara.application.compiler.source_coverage import SourceGraphCoverageReport


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
    # Typed and graph-bound authorization values consumed by the TaskFlow gate.
    # Presence documents compiler consumption, not backend/runtime enforcement.
    authorization_semantic_obligations: AuthorizationSemanticObligations | None = None
    # Mandatory for certification/generation paths; optional only for legacy result construction.
    source_projection_context: SourceProjectionContext | None = None
    # Supplied only by trusted intake/review; never inferred from graph hashes.
    source_graph_coverage_report: SourceGraphCoverageReport | None = None

class TaskFlowSemanticProjection(BaseModel):
    """SystemModel plus an explicit declaration of which TaskFlow semantics it consumed.

    This declaration is a reviewable integration contract, not proof that the
    projector is correct. The projector implementation and its tests must
    demonstrate that each listed value affects the resulting model.
    """

    system_model: SystemModel
    projected_values: dict[str, object]

    @model_validator(mode="after")
    def validate_projected_values(self) -> "TaskFlowSemanticProjection":
        if any(not field.strip() for field in self.projected_values):
            raise ValueError("projected_values cannot contain blank paths")
        embedded = self.system_model.extensions.get("taskflow_semantic_values")
        if embedded != self.projected_values:
            raise ValueError(
                "SystemModel.extensions.taskflow_semantic_values must preserve "
                "the exact projected semantic values"
            )
        return self

    @classmethod
    def model_validate_projection(
        cls, system_model: SystemModel, projected_values: dict[str, object]
    ) -> "TaskFlowSemanticProjection":
        return cls(system_model=system_model, projected_values=projected_values)

