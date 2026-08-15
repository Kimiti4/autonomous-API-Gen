"""D4: LanguageModelBridge.complete_with_context — the AIR integration seam.

Verifies a compiled prompt (deterministic from a ContextGraph) is routed
through the cascade and that byte-identical provenance survives.
"""
from pydantic import BaseModel

from tiannara.application.intelligence import (
    CascadeExecutor,
    DEFAULT_POLICY,
    LanguageModelBridge,
    PromptCompiler,
    TaskInstruction,
    TokenBudget,
)
from tiannara.application.intelligence import ProviderRegistry
from tiannara.application.intelligence.bridge import LanguageModelIntelligenceAdapter
from tiannara.domain.models.context_graph import ContextGraph, ContextKind, ContextNode
from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    IntelligenceTask,
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
from tiannara.domain.models.system_model import Priority
from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
from tiannara.infrastructure.llm.transcript import ModelCallTranscript


class _Out(BaseModel):
    nodes: list[str]


def _graph():
    return ContextGraph.derive(
        TaskKind.EXTRACTION,
        [
            ContextNode(
                node_id="m1",
                kind=ContextKind.SECURITY_POSTURE,
                priority=Priority.MUST,
                title="Security",
                payload={"authentication": "token_based"},
            )
        ],
        subject_ref="m1",
    )


def _budget():
    return TokenBudget(
        total_tokens=3000, output_reserve_tokens=500,
        instruction_reserve_tokens=400, schema_reserve_tokens=200,
    )


def _instruction():
    return TaskInstruction(
        role="Requirements Analyst agent",
        objective="Extract.",
        output_schema_id="ctx.out.v1",
    )


def _bridge(tmp_path):
    graph = _graph()
    compiled = PromptCompiler().compile(graph, _budget(), _instruction())

    request = StructuredCompletionRequest(
        model_id="test-model",
        task="intent.extraction",
        prompt=compiled.prompt,
        output_schema_id="ctx.out.v1",
        decoding=DecodingParameters(),
    )
    transcript = ModelCallTranscript(tmp_path / "t.jsonl")
    transcript.append(
        ModelCallRecord(
            signature_hash=compute_call_signature(request),
            model_id=request.model_id,
            task=request.task,
            output_schema_id=request.output_schema_id,
            output_payload={"nodes": ["r1"]},
            response_hash=hash_payload({"nodes": ["r1"]}),
            decoding=request.decoding,
        )
    )
    adapter = LanguageModelIntelligenceAdapter(
        RecordedModelProvider(transcript),
        CapabilityDeclaration(
            provider_id="replay-1",
            provider_class=ProviderClass.REMOTE_MODEL,
            task_kinds=[TaskKind.EXTRACTION],
        ),
    )
    registry = ProviderRegistry()
    registry.register(adapter)
    incoming = StructuredCompletionRequest(
        model_id="test-model",
        task="intent.extraction",
        prompt="(compiled from context graph)",
        output_schema_id="ctx.out.v1",
        decoding=DecodingParameters(),
    )
    return LanguageModelBridge(CascadeExecutor(registry), DEFAULT_POLICY), incoming, graph, compiled


def test_context_aware_completion_replays_with_compiled_prompt(tmp_path):
    bridge, incoming, _graph, expected = _bridge(tmp_path)
    outcome = bridge.complete_with_context(incoming, _Out, _graph, _budget(), _instruction())

    assert outcome.compiled_prompt.prompt == expected.prompt
    assert outcome.result.output.nodes == ["r1"]
    assert outcome.result.record.status is ModelCallStatus.REPLAYED
    assert outcome.result.record.signature_hash == compute_call_signature(
        StructuredCompletionRequest(
            model_id="test-model",
            task="intent.extraction",
            prompt=expected.prompt,
            output_schema_id="ctx.out.v1",
            decoding=DecodingParameters(),
        )
    )


def test_context_aware_completion_is_deterministic(tmp_path):
    bridge, incoming, graph, _ = _bridge(tmp_path)
    first = bridge.complete_with_context(incoming, _Out, graph, _budget(), _instruction())
    second = bridge.complete_with_context(incoming, _Out, graph, _budget(), _instruction())
    assert first.compiled_prompt.content_hash() == second.compiled_prompt.content_hash()
    assert first.result.output == second.result.output
