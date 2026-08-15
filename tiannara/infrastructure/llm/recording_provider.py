"""RecordingModelProvider -- provenance-capturing decorator.

Wraps any ``LanguageModelProvider``, measures latency, recomputes canonical
hashes, marks the record LIVE, and appends it to a transcript. On inner
failure it records a FAILED record and re-raises. This is the mechanism by
which live runs (B6) produce committable replay fixtures and by which B3
populates ``GraphProvenance.model_versions`` via ``record.provenance_tag()``.
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

from pydantic import BaseModel

from tiannara.domain.models.model_call import (
    ModelCallRecord,
    ModelCallStatus,
    StructuredCompletionRequest,
    compute_call_signature,
    hash_payload,
    hash_prompt,
)
from tiannara.domain.ports.language_model import (
    LanguageModelProvider,
    StructuredCompletionResult,
)

from .transcript import ModelCallTranscript

OutputT = TypeVar("OutputT", bound=BaseModel)


class RecordingModelProvider:
    def __init__(
        self,
        inner: LanguageModelProvider,
        transcript: ModelCallTranscript,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._inner = inner
        self._transcript = transcript
        self._clock = clock or time.perf_counter

    def complete_structured(
        self,
        request: StructuredCompletionRequest,
        output_type: type[OutputT],
    ) -> StructuredCompletionResult[OutputT]:
        start = self._clock()
        try:
            result = self._inner.complete_structured(request, output_type)
        except Exception:
            elapsed_ms = (self._clock() - start) * 1000.0
            failure = ModelCallRecord(
                signature_hash=compute_call_signature(request),
                model_id=request.model_id,
                task=request.task,
                output_schema_id=request.output_schema_id,
                prompt_hash=hash_prompt(request.prompt),
                response_hash="",
                output_payload=None,
                latency_ms=round(elapsed_ms, 3),
                status=ModelCallStatus.FAILED,
                decoding=request.decoding,
            )
            self._transcript.append(failure)
            raise

        elapsed_ms = (self._clock() - start) * 1000.0
        output_payload = result.output.model_dump(mode="json")
        record = ModelCallRecord(
            signature_hash=compute_call_signature(request),
            model_id=request.model_id,
            task=request.task,
            output_schema_id=request.output_schema_id,
            prompt_hash=hash_prompt(request.prompt),
            response_hash=hash_payload(output_payload),
            output_payload=output_payload,
            input_tokens=result.record.input_tokens,
            output_tokens=result.record.output_tokens,
            latency_ms=round(elapsed_ms, 3),
            status=ModelCallStatus.LIVE,
            decoding=request.decoding,
        )
        self._transcript.append(record)
        return StructuredCompletionResult(output=result.output, record=record)
