"""D2: Backend coupling guard - the bridge never couples to an external backend.

Verifies LanguageModelBridge faithfully proxies a local (L2) provider with
byte-identical provenance, and that under KEYLESS_POLICY a registered REMOTE
provider never enters the cascade_path (no local backend escalates).
"""
import pytest

from tiannara.application.intent import IntentCompilerConfig, build_extraction_request, normalize
from tiannara.application.intent.schemas import ElicitationOutput, ExtractionOutput
from tiannara.application.intelligence import CascadeExecutor, KEYLESS_POLICY, LanguageModelBridge, ProviderRegistry
from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    IntelligenceResult,
    IntelligenceTask,
    LocalityLevel,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.models.model_call import (
    LanguageModelError,
    ModelCallRecord,
    ModelCallStatus,
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


def _local_keyless_provider(tmp_path, topology_id="recorded@1"):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    request = build_extraction_request(normalized, ElicitationOutput(), config)
    replay = _seed(tmp_path, [(request, _valid_extraction_payload())])
    topology = LocalTopology(
        topology_version="1.0",
        provider_id=topology_id,
        task_kinds=["extraction", "synthesis"],
    )
    return LocalModelProvider.from_topology(replay, topology), request


class _StubRemote:
    """A REMOTE provider stub that records (and would fail-fast if) called."""

    def __init__(self, provider_id, task_kinds=None):
        self._declaration = CapabilityDeclaration(
            provider_id=provider_id,
            provider_class=ProviderClass.REMOTE_MODEL,
            task_kinds=task_kinds or [TaskKind.EXTRACTION],
        )
        self.calls = 0

    @property
    def declaration(self):
        return self._declaration

    def complete(self, task):
        self.calls += 1
        raise LanguageModelError(f"{self._declaration.provider_id} must not be called under keyless")


def test_bridge_replays_local_provenance(tmp_path):
    local, request = _local_keyless_provider(tmp_path)
    registry = ProviderRegistry()
    registry.register(local)
    bridge = LanguageModelBridge(CascadeExecutor(registry), KEYLESS_POLICY)

    result = bridge.complete_structured(request, ExtractionOutput)

    assert result.record.status is ModelCallStatus.REPLAYED
    assert result.record.model_id == "recorded@1"
    assert isinstance(result.output, ExtractionOutput)
    assert all(
        p.declaration.locality is LocalityLevel.L2_LOCAL_MODEL
        for p in registry.providers()
    )


def test_cascade_path_excludes_external(tmp_path):
    local, request = _local_keyless_provider(tmp_path)
    remote = _StubRemote("frontier")
    registry = ProviderRegistry()
    registry.register(local)
    registry.register(remote)
    executor = CascadeExecutor(registry)

    task = IntelligenceTask(
        task_kind=TaskKind.SYNTHESIS,
        task_label=request.task,
        prompt=request.prompt,
        output_schema_id=request.output_schema_id,
        decoding=request.decoding,
        model_hint=request.model_id,
        output_type=ExtractionOutput,
    )
    result = executor.execute(task, KEYLESS_POLICY)

    assert result.provider_id == "recorded@1"
    assert result.policy_name == "keyless"
    assert all(
        step.locality is LocalityLevel.L2_LOCAL_MODEL for step in result.cascade_path
    )
    assert "frontier" not in [step.provider_id for step in result.cascade_path]
    assert remote.calls == 0
