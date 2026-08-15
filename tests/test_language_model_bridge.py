import pytest

from pathlib import Path

from pydantic import BaseModel

from tiannara.application.intent import (
    IntentCompilerConfig,
    build_elicitation_request,
    normalize,
)
from tiannara.application.intelligence import (
    CascadeExecutor,
    DEFAULT_POLICY,
    KEYLESS_POLICY,
    LanguageModelBridge,
    LanguageModelIntelligenceAdapter,
    ProviderRegistry,
)
from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.models.model_call import (
    DecodingParameters,
    ModelCallRecord,
    ModelCallStatus,
    StructuredCompletionRequest,
    compute_call_signature,
    hash_payload,
)
from tiannara.application.intent.schemas import ElicitationOutput
from tiannara.infrastructure.llm import ModelCallTranscript, RecordedModelProvider


class _Out(BaseModel):
    value: int


def _request() -> StructuredCompletionRequest:
    return StructuredCompletionRequest(
        model_id="test-model", task="intent.extraction",
        prompt="Extract the requirement graph.",
        output_schema_id="test.out.v1", decoding=DecodingParameters(),
    )


def _seeded_replay(tmp_path) -> tuple[RecordedModelProvider, StructuredCompletionRequest]:
    config = IntentCompilerConfig()
    request = build_elicitation_request(normalize("Book berths."), config)
    payload = {"inferred_capabilities": ["berth booking"], "assumptions": [], "clarifications": []}
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    transcript.append(
        ModelCallRecord(
            signature_hash=compute_call_signature(request),
            model_id=request.model_id, task=request.task,
            output_schema_id=request.output_schema_id,
            output_payload=payload, response_hash=hash_payload(payload),
            decoding=request.decoding,
        )
    )
    return RecordedModelProvider(transcript), request


def _bridge(tmp_path, provider_class):
    replay, request = _seeded_replay(tmp_path)
    adapter = LanguageModelIntelligenceAdapter(
        replay,
        CapabilityDeclaration(
            provider_id="replay-1",
            provider_class=provider_class,
            task_kinds=[TaskKind.EXTRACTION, TaskKind.SYNTHESIS],
        ),
    )
    registry = ProviderRegistry()
    registry.register(adapter)
    bridge = LanguageModelBridge(CascadeExecutor(registry), DEFAULT_POLICY)
    return bridge, request


def test_bridge_satisfies_language_model_port_with_identical_provenance(tmp_path):
    bridge, request = _bridge(tmp_path, ProviderClass.REMOTE_MODEL)
    result = bridge.complete_structured(request, ElicitationOutput)
    assert result.output.inferred_capabilities == ["berth booking"]
    assert result.record.status is ModelCallStatus.REPLAYED
    assert result.record.signature_hash == compute_call_signature(request)


def test_keyless_policy_blocks_remote_only_providers(tmp_path):
    replay, request = _seeded_replay(tmp_path)
    adapter = LanguageModelIntelligenceAdapter(
        replay,
        CapabilityDeclaration(
            provider_id="replay-1",
            provider_class=ProviderClass.REMOTE_MODEL,
            task_kinds=[TaskKind.EXTRACTION, TaskKind.SYNTHESIS],
        ),
    )
    registry = ProviderRegistry()
    registry.register(adapter)
    bridge = LanguageModelBridge(CascadeExecutor(registry), KEYLESS_POLICY)

    from tiannara.application.intelligence import CascadeExhaustedError
    with pytest.raises(CascadeExhaustedError):
        bridge.complete_structured(request, ElicitationOutput)
