"""Model-call provenance contracts for the LanguageModelProvider port.

Captures, technology-agnostically, everything required to audit and
deterministically replay a structured language-model call:

  * a canonical, content-addressed call signature;
  * prompt/response integrity hashes;
  * decoding parameters;
  * token accounting and latency;
  * the structured output payload (required for hermetic replay).

Live vendors are compiler-style backends added behind the
``LanguageModelProvider`` port; the platform core never depends on one.
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..services.canonical import canonical_hash


class LanguageModelError(Exception):
    """Base error for language-model provider failures."""


class UnrecordedCallError(LanguageModelError):
    """Raised by replay when a call signature has no recorded fixture."""

    def __init__(self, signature_hash: str, task: str, model_id: str) -> None:
        self.signature_hash = signature_hash
        self.task = task
        self.model_id = model_id
        super().__init__(
            "No recorded fixture for call "
            f"task={task!r} model={model_id!r} signature={signature_hash[:12]}... "
            "Record it live once, commit the transcript, then replay."
        )


class TranscriptIntegrityError(LanguageModelError):
    """Raised when a recorded payload no longer matches its response hash."""


class DecodingParameters(BaseModel):
    """Provider-agnostic decoding controls. Determinism is a first-class knob."""

    model_config = ConfigDict(frozen=True)

    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int | None = None
    seed: int | None = None


class StructuredCompletionRequest(BaseModel):
    """A schema-constrained completion request.

    ``model_id``, ``task``, ``prompt``, ``output_schema_id``, and ``decoding``
    jointly determine the call signature; changing any of them changes the
    signature and therefore the replay fixture that will match.
    """

    model_config = ConfigDict(frozen=True)

    model_id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    output_schema_id: str = Field(min_length=1)
    decoding: DecodingParameters = Field(default_factory=DecodingParameters)


class ModelCallStatus(str, enum.Enum):
    LIVE = "live"
    REPLAYED = "replayed"
    FAILED = "failed"


class ModelCallRecord(BaseModel):
    """Immutable provenance for one structured call.

    ``output_payload`` stores the structured output so replay can reconstruct
    it without a network. ``previous_hash`` / ``record_hash`` are set by the
    transcript store to make the record stream tamper-evident.
    """

    model_config = ConfigDict(use_enum_values=False)

    signature_hash: str = ""
    model_id: str = ""
    task: str = ""
    output_schema_id: str = ""
    prompt_hash: str = ""
    response_hash: str = ""
    output_payload: dict[str, Any] | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    status: ModelCallStatus = ModelCallStatus.LIVE
    decoding: DecodingParameters = Field(default_factory=DecodingParameters)
    prompt_ref: str | None = None
    response_ref: str | None = None
    previous_hash: str | None = None
    record_hash: str | None = None

    def provenance_tag(self) -> str:
        """Compact tag for ``GraphProvenance.model_versions``:
        ``<model_id>:<signature_hash>``."""
        return f"{self.model_id}:{self.signature_hash}"


def compute_call_signature(request: StructuredCompletionRequest) -> str:
    """Content-addressed signature over everything that defines the call."""
    payload = {
        "model_id": request.model_id,
        "task": request.task,
        "prompt": request.prompt,
        "output_schema_id": request.output_schema_id,
        "decoding": request.decoding.model_dump(mode="json"),
    }
    return canonical_hash(payload)


def hash_prompt(prompt: str) -> str:
    return canonical_hash(prompt)


def hash_payload(payload: dict[str, Any]) -> str:
    return canonical_hash(payload)
