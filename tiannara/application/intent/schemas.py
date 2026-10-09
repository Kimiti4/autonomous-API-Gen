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


class FieldSeed(BaseModel):
    """Technology-neutral field design for a persisted entity.

    ``type`` must name a value of the abstract field vocabulary
    (``AbstractFieldType``: identifier, text, integer, decimal, boolean,
    timestamp, enumeration, reference, binary, document) -- never a concrete
    database or language type.
    """

    name: str = Field(min_length=1)
    type: str = "text"
    required: bool = True
    enumeration_values: list[str] = Field(default_factory=list)
    description: str = ""


class DataSeed(BaseModel):
    """A data entity designed during extraction, linked back to requirements.

    ``ref`` joins the requirement graph's identifier space (typically a
    ``data``-kind node) so data models remain traceable end to end.
    ``owning_service_ref`` optionally names the functional node whose derived
    service owns the entity.
    """

    ref: str = Field(min_length=1)
    name: str = Field(min_length=1, pattern=r"^[A-Za-z][A-Za-z0-9_ -]*$")
    fields: list[FieldSeed] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    owning_service_ref: str | None = None
    requirement_refs: list[str] = Field(default_factory=list)


class ExtractionOutput(BaseModel):
    nodes: list[NodeSeed] = Field(default_factory=list)
    edges: list[EdgeSeed] = Field(default_factory=list)
    data_models: list[DataSeed] = Field(default_factory=list)


class RepairOutput(ExtractionOutput):
    changes_summary: str = ""


class IntentCompilationResult(BaseModel):
    system_id: str
    isr: IntermediateSoftwareRepresentation
    requirement_graph: RequirementGraph
    call_records: list[ModelCallRecord] = Field(default_factory=list)
    repair_iterations: int = 0
    assumption_ids: list[str] = Field(default_factory=list)
