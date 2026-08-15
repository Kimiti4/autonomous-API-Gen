"""Intent compiler configuration. Injectable, strongly typed, deterministic."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from tiannara.domain.models.model_call import DecodingParameters


class IntentCompilerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    #: Identifier recorded in provenance; replay fixtures are keyed per model.
    model_id: str = "recorded@1"
    decoding: DecodingParameters = Field(default_factory=DecodingParameters)
    #: Bounded repair budget. Deterministic convergence/divergence depends on it.
    max_repair_iterations: int = Field(default=3, ge=0)
    enable_elicitation: bool = True


INTENT_ELICITATION_TASK = "intent.elicitation"
INTENT_EXTRACTION_TASK = "intent.extraction"
INTENT_REPAIR_TASK = "intent.repair"

INTENT_ELICITATION_SCHEMA = "intent.elicitation.v1"
INTENT_EXTRACTION_SCHEMA = "intent.extraction.v1"
INTENT_REPAIR_SCHEMA = "intent.repair.v1"
