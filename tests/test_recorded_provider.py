import pytest
from pydantic import BaseModel, ValidationError

from tiannara.domain.models.model_call import (
    ModelCallRecord,
    ModelCallStatus,
    StructuredCompletionRequest,
    TranscriptIntegrityError,
    UnrecordedCallError,
    compute_call_signature,
    hash_payload,
)
from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
from tiannara.infrastructure.llm.transcript import ModelCallTranscript


class _Extraction(BaseModel):
    nodes: list[str]
    confidence: float


def _request() -> StructuredCompletionRequest:
    return StructuredCompletionRequest(
        model_id="stub@1", task="extraction",
        prompt="Extract.", output_schema_id="extraction.v1",
    )


def _seed(tmp_path, payload) -> RecordedModelProvider:
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    request = _request()
    transcript.append(
        ModelCallRecord(
            signature_hash=compute_call_signature(request),
            model_id=request.model_id, task=request.task,
            output_schema_id=request.output_schema_id,
            output_payload=payload, response_hash=hash_payload(payload),
        )
    )
    return RecordedModelProvider(transcript)


def test_replay_is_deterministic_and_validated(tmp_path):
    provider = _seed(tmp_path, {"nodes": ["a", "b"], "confidence": 0.9})
    first = provider.complete_structured(_request(), _Extraction)
    second = provider.complete_structured(_request(), _Extraction)
    assert first.output == second.output
    assert first.record.status is ModelCallStatus.REPLAYED
    assert first.output.nodes == ["a", "b"]


def test_unrecorded_call_fails_loudly(tmp_path):
    provider = _seed(tmp_path, {"nodes": [], "confidence": 0.1})
    missing = _request().model_copy(update={"prompt": "Different prompt."})
    with pytest.raises(UnrecordedCallError):
        provider.complete_structured(missing, _Extraction)


def test_schema_drift_fails_fast(tmp_path):
    provider = _seed(tmp_path, {"nodes": ["a"]})  # missing 'confidence'
    with pytest.raises(ValidationError):
        provider.complete_structured(_request(), _Extraction)


def test_integrity_mismatch_detected(tmp_path):
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    request = _request()
    payload = {"nodes": ["a"], "confidence": 0.5}
    transcript.append(
        ModelCallRecord(
            signature_hash=compute_call_signature(request),
            model_id=request.model_id, task=request.task,
            output_schema_id=request.output_schema_id,
            output_payload=payload, response_hash="wrong-hash",
        )
    )
    provider = RecordedModelProvider(transcript)
    with pytest.raises(TranscriptIntegrityError):
        provider.complete_structured(request, _Extraction)
