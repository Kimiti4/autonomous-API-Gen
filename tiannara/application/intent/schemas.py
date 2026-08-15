"""Stage I/O contracts for the intent compiler.

These are the structured outputs the LanguageModelProvider must produce.
They are versioned via ``output_schema_id`` constants in ``config.py`` so
replay fixtures and schema drift are detectable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.domain.models.model_call import ModelCallRecord
from tiannara.domain.models.requirement_graph import RequirementGraph


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
