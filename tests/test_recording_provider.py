import pytest
from pydantic import BaseModel

from tiannara.domain.models.model_call import (
    LanguageModelError,
    ModelCallRecord,
    ModelCallStatus,
    StructuredCompletionRequest,
    compute_call_signature,
    hash_payload,
)
from tiannara.domain.ports.language_model import StructuredCompletionResult
from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
from tiannara.infrastructure.llm.recording_provider import RecordingModelProvider
from tiannara.infrastructure.llm.transcript import ModelCallTranscript


class _Out(BaseModel):
    value: int


class _StubProvider:
    def __init__(self, output: _Out, fail: bool = False) -> None:
        self._output = output
        self._fail = fail

    def complete_structured(self, request, output_type):
        if self._fail:
            raise LanguageModelError("stub failure")
        return StructuredCompletionResult(
            output=self._output,
            record=ModelCallRecord(
                model_id=request.model_id, input_tokens=5, output_tokens=7
            ),
        )


def _request() -> StructuredCompletionRequest:
    return StructuredCompletionRequest(
        model_id="stub@1", task="task", prompt="p", output_schema_id="out.v1",
    )


def test_recording_captures_provenance(tmp_path):
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    recorder = RecordingModelProvider(_StubProvider(_Out(value=3)), transcript)
    result = recorder.complete_structured(_request(), _Out)

    record = result.record
    assert record.status is ModelCallStatus.LIVE
    assert record.signature_hash == compute_call_signature(_request())
    assert record.response_hash == hash_payload({"value": 3})
    assert record.input_tokens == 5 and record.output_tokens == 7
    assert record.latency_ms >= 0.0
    assert transcript.verify_chain() is True


def test_record_then_replay_round_trip(tmp_path):
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    recorder = RecordingModelProvider(_StubProvider(_Out(value=42)), transcript)
    live = recorder.complete_structured(_request(), _Out)

    replayer = RecordedModelProvider(transcript)
    replayed = replayer.complete_structured(_request(), _Out)
    assert replayed.output == live.output
    assert replayed.record.status is ModelCallStatus.REPLAYED


def test_failure_is_recorded_and_reraised(tmp_path):
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    recorder = RecordingModelProvider(_StubProvider(_Out(value=1), fail=True), transcript)
    with pytest.raises(LanguageModelError):
        recorder.complete_structured(_request(), _Out)
    records = list(transcript.iter_records())
    assert len(records) == 1
    assert records[0].status is ModelCallStatus.FAILED
    assert records[0].output_payload is None
