"""RecordedModelProvider -- deterministic, hermetic replay.

Implements ``LanguageModelProvider`` by matching the request's call signature
against a recorded transcript and returning the recorded, schema-validated
output. No network, no vendor, no fabrication.

Guarantees:
  * identical request -> identical output (byte-stable);
  * unrecorded call -> UnrecordedCallError (fail-fast, never invent);
  * payload/response-hash mismatch -> TranscriptIntegrityError;
  * fixture/schema drift -> pydantic ValidationError (fail-fast).
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError

from tiannara.domain.models.model_call import (
    ModelCallStatus,
    TranscriptIntegrityError,
    UnrecordedCallError,
    compute_call_signature,
    hash_payload,
)
from tiannara.domain.ports.language_model import (
    StructuredCompletionRequest,
    StructuredCompletionResult,
)

from .transcript import ModelCallTranscript

OutputT = TypeVar("OutputT", bound=BaseModel)


class RecordedModelProvider:
    def __init__(self, transcript: ModelCallTranscript) -> None:
        self._index = transcript.index_by_signature()

    def complete_structured(
        self,
        request: StructuredCompletionRequest,
        output_type: type[OutputT],
    ) -> StructuredCompletionResult[OutputT]:
        signature = compute_call_signature(request)
        record = self._index.get(signature)
        if record is None:
            raise UnrecordedCallError(signature, request.task, request.model_id)

        if record.output_payload is None:
            raise TranscriptIntegrityError(
                f"Record {record.signature_hash[:12]}... has no replayable payload."
            )
        if record.response_hash and hash_payload(record.output_payload) != record.response_hash:
            raise TranscriptIntegrityError(
                f"Recorded payload for {record.signature_hash[:12]}... does not "
                "match its response hash; transcript may be tampered."
            )

        output = output_type.model_validate(record.output_payload)
        replayed = record.model_copy(update={"status": ModelCallStatus.REPLAYED})
        return StructuredCompletionResult(output=output, record=replayed)
