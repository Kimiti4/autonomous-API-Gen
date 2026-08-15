"""D3: Local provider isolation - the L2 boundary is structural, not aspirational.

Verifies LocalModelProvider materializes a L2 (LOCAL_MODEL) capability with
opaque topology metadata, replays hermetically through the adapter, and is
scoped to its declared task kinds.
"""
import pytest

from tiannara.application.intent import IntentCompilerConfig, build_extraction_request, normalize
from tiannara.application.intent.schemas import ElicitationOutput, ExtractionOutput
from tiannara.application.intelligence import KEYLESS_POLICY, ProviderRegistry
from tiannara.domain.models.intelligence import (
    IntelligenceTask,
    LocalityLevel,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.models.model_call import (
    ModelCallStatus,
    ModelCallRecord,
    compute_call_signature,
    hash_payload,
)
from tiannara.infrastructure.intelligence import LocalModelProvider, LocalTopology
from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
from tiannara.infrastructure.llm.transcript import ModelCallTranscript

STATEMENT = "We need a system to book berths at marinas and track availability."


def _valid_extraction_payload():
    return {
        "nodes": [
            {"ref": "req-book", "kind": "functional", "statement": "Book a berth", "priority": "must"},
            {"ref": "req-avail", "kind": "functional", "statement": "Track availability", "priority": "must"},
        ],
        "edges": [],
    }


def _seed(tmp_path, entries):
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    for request, payload in entries:
        transcript.append(
            ModelCallRecord(
                signature_hash=compute_call_signature(request),
                model_id=request.model_id,
                task=request.task,
                output_schema_id=request.output_schema_id,
                output_payload=payload,
                response_hash=hash_payload(payload),
                decoding=request.decoding,
            )
        )
    return RecordedModelProvider(transcript)


def _local_provider(tmp_path, provider_id="local-inference", task_kinds=("extraction", "synthesis")):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    request = build_extraction_request(normalized, ElicitationOutput(), config)
    replay = _seed(tmp_path, [(request, _valid_extraction_payload())])
    topology = LocalTopology(
        topology_version="1.0",
        provider_id=provider_id,
        task_kinds=list(task_kinds),
        metadata={"runtime": "ollama"},
    )
    return LocalModelProvider.from_topology(replay, topology), request


def test_local_provider_manifest_is_l2_and_opaque(tmp_path):
    local, _ = _local_provider(tmp_path, provider_id="local-inference")
    decl = local.declaration
    assert decl.provider_class is ProviderClass.LOCAL_MODEL
    assert decl.locality is LocalityLevel.L2_LOCAL_MODEL
    assert decl.locality is not LocalityLevel.L3_EXTERNAL_MODEL
    assert decl.provider_id == "local-inference"
    assert decl.metadata["transport"] == "openai_compatible"
    assert not any("key" in k.lower() for k in decl.metadata)
    assert "remote" not in decl.metadata.get("transport", "").lower()


def test_local_provider_serves_replay(tmp_path):
    local, request = _local_provider(tmp_path, provider_id="recorded@1")
    task = IntelligenceTask(
        task_kind=TaskKind.SYNTHESIS,
        task_label=request.task,
        prompt=request.prompt,
        output_schema_id=request.output_schema_id,
        decoding=request.decoding,
        model_hint=request.model_id,
        output_type=ExtractionOutput,
    )
    result = local.complete(task)
    assert result.provider_class is ProviderClass.LOCAL_MODEL
    assert result.locality is LocalityLevel.L2_LOCAL_MODEL
    assert result.model_record.status is ModelCallStatus.REPLAYED
    assert result.model_record.model_id == "recorded@1"


def test_local_provider_scope_isolation(tmp_path):
    local, _ = _local_provider(tmp_path, task_kinds=("extraction", "synthesis"))
    registry = ProviderRegistry()
    registry.register(local)

    handled = registry.matches(
        IntelligenceTask(task_kind=TaskKind.EXTRACTION, task_label="t", prompt="p", output_schema_id="s.v1"),
        KEYLESS_POLICY.max_locality,
    )
    assert len(handled) == 1

    out_of_scope = registry.matches(
        IntelligenceTask(task_kind=TaskKind.CLASSIFICATION, task_label="t", prompt="p", output_schema_id="s.v1"),
        KEYLESS_POLICY.max_locality,
    )
    assert out_of_scope == []
