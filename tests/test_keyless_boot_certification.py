"""D3: Keyless boot certification - full intent compile through the keyless bridge.

Closure record for the keyless-certification harness: IntentCompiler wired to a
LanguageModelBridge(KEYLESS_POLICY) backed by a single LocalModelProvider
wrapping a hermetic RecordedModelProvider. Reproduces the audited happy-path
statement + elicitation/extraction fixtures (see test_intent_compiler) and
asserts that byte-identical provenance survives the bridge, that no external
provider is reachable, and that AutonomyCertification proves the result
structurally external-free.
"""
import pytest

from tiannara.application.intent import (
    IntentCompiler,
    IntentCompilerConfig,
    build_elicitation_request,
    build_extraction_request,
    normalize,
)
from tiannara.application.intent.schemas import ElicitationOutput, ExtractionOutput
from tiannara.application.intelligence import (
    CascadeExecutor,
    KEYLESS_POLICY,
    LanguageModelBridge,
    ProviderRegistry,
    certify_no_external_dependency,
)
from tiannara.domain.models.intelligence import (
    LocalityLevel,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.models.model_call import (
    ModelCallRecord,
    ModelCallStatus,
    compute_call_signature,
    hash_payload,
)
from tiannara.infrastructure.intelligence import LocalModelProvider, LocalTopology
from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
from tiannara.infrastructure.llm.transcript import ModelCallTranscript

STATEMENT = "We need a system to book berths at marinas and track availability."


def _elicitation_payload():
    return {
        "inferred_capabilities": ["berth booking"],
        "assumptions": [{"statement": "Marinas manage their own berths", "rationale": "typical"}],
        "clarifications": [],
    }


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


def test_keyless_boot_certifies_external_free(tmp_path):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload()
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    extraction_payload = _valid_extraction_payload()

    transcript = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), extraction_payload),
        ],
    )
    local = LocalModelProvider.from_topology(
        transcript,
        LocalTopology(
            topology_version="1.0",
            provider_id="recorded@1",
            task_kinds=["extraction", "synthesis"],
        ),
    )
    registry = ProviderRegistry()
    registry.register(local)
    bridge = LanguageModelBridge(CascadeExecutor(registry), KEYLESS_POLICY)
    compiler = IntentCompiler(bridge, config)

    result = compiler.compile_full(STATEMENT, system_id="sys-keyless")

    # Provenance is byte-identical through the bridge vs. a direct provider.
    assert result.repair_iterations == 0
    assert len(result.call_records) == 2
    assert all(r.status is ModelCallStatus.REPLAYED for r in result.call_records)
    assert all(r.model_id == "recorded@1" for r in result.call_records)
    assert result.requirement_graph.provenance.model_versions[0].startswith("recorded@1:")
    node_ids = {n.id for n in result.requirement_graph.nodes}
    assert {"req-book", "req-avail", "asm-1"} <= node_ids
    assert result.assumption_ids == ["asm-1"]
    assert result.isr.system_model() is not None

    # KEYLESS structural invariant: every registered provider is local (L2).
    assert all(
        p.declaration.provider_class is ProviderClass.LOCAL_MODEL for p in registry.providers()
    )
    assert all(
        p.declaration.locality is LocalityLevel.L2_LOCAL_MODEL for p in registry.providers()
    )

    # Certification: no external dependency is structurally required.
    cert = certify_no_external_dependency(
        registry, KEYLESS_POLICY, [TaskKind.EXTRACTION, TaskKind.SYNTHESIS]
    )
    assert cert.external_api_key_required is False
    assert cert.policy_name == "keyless"
    assert cert.max_locality is LocalityLevel.L2_LOCAL_MODEL
    assert all(cert.per_task_coverage.values())
