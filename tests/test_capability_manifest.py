"""D2: Capability manifest schema + provenance (Cap-D).

Pins CapabilityDeclaration invariants and the LocalTopology -> manifest
adapter: locality is derived from provider_class, metadata is opaque
deployment provenance, and output_schema_ids of [] means 'any'.
"""
from pathlib import Path

import pytest
from pydantic import ValidationError

from tiannara.application.intent import IntentCompilerConfig, build_extraction_request, normalize
from tiannara.application.intent.schemas import ElicitationOutput, ExtractionOutput
from tiannara.domain.models.intelligence import (
    PROVIDER_CLASS_LOCALITY,
    CapabilityDeclaration,
    LocalityLevel,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.models.model_call import ModelCallRecord, compute_call_signature, hash_payload
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


def _local_provider(tmp_path, provider_id="local-demo", task_kinds=("extraction", "synthesis")):
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
    return LocalModelProvider.from_topology(replay, topology)


def test_capability_declaration_locality_mapping():
    for cls in ProviderClass:
        decl = CapabilityDeclaration(
            provider_id="p", provider_class=cls, task_kinds=[TaskKind.EXTRACTION]
        )
        assert decl.locality is PROVIDER_CLASS_LOCALITY[cls]
    assert (
        CapabilityDeclaration(
            provider_id="p", provider_class=ProviderClass.LOCAL_MODEL, task_kinds=[TaskKind.EXTRACTION]
        ).locality
        is LocalityLevel.L2_LOCAL_MODEL
    )
    assert (
        CapabilityDeclaration(
            provider_id="p", provider_class=ProviderClass.REMOTE_MODEL, task_kinds=[TaskKind.EXTRACTION]
        ).locality
        is LocalityLevel.L3_EXTERNAL_MODEL
    )


def test_local_model_provider_manifest_from_topology(tmp_path):
    local = _local_provider(tmp_path, provider_id="local-demo", task_kinds=("extraction", "synthesis"))
    decl = local.declaration
    assert decl.provider_class is ProviderClass.LOCAL_MODEL
    assert decl.locality is LocalityLevel.L2_LOCAL_MODEL
    assert decl.task_kinds == [TaskKind.EXTRACTION, TaskKind.SYNTHESIS]
    assert decl.provider_id == "local-demo"
    assert decl.metadata["transport"] == "openai_compatible"
    assert decl.metadata["topology_version"] == "1.0"
    # Opaque deployment provenance is carried, never interpreted by core.
    assert decl.metadata["runtime"] == "ollama"


def test_capability_declaration_is_frozen():
    decl = CapabilityDeclaration(
        provider_id="p", provider_class=ProviderClass.LOCAL_MODEL, task_kinds=[TaskKind.EXTRACTION]
    )
    assert CapabilityDeclaration.model_config["frozen"] is True
    with pytest.raises((ValidationError, TypeError)):
        decl.provider_id = "mutated"  # type: ignore[misc]


def test_manifest_output_schema_defaults_to_any(tmp_path):
    local = _local_provider(tmp_path)
    assert local.declaration.output_schema_ids == []

    restricted = CapabilityDeclaration(
        provider_id="r",
        provider_class=ProviderClass.LOCAL_MODEL,
        task_kinds=[TaskKind.EXTRACTION],
        output_schema_ids=["x.v1"],
    )
    assert restricted.output_schema_ids == ["x.v1"]


def test_local_topology_load_roundtrip(tmp_path):
    data = (
        "topology_version: '1.0'\n"
        "provider_id: local-demo\n"
        "provider_class: local_model\n"
        "transport: openai_compatible\n"
        "task_kinds:\n"
        "  - extraction\n"
        "  - synthesis\n"
    )
    path = tmp_path / "topology.yaml"
    path.write_text(data, encoding="utf-8")
    topology = LocalTopology.load(path)
    assert topology.provider_id == "local-demo"
    assert topology.task_kinds == ["extraction", "synthesis"]
    assert topology.provider_class == "local_model"
    assert topology.transport == "openai_compatible"


def test_local_provider_from_loaded_topology_is_replayable(tmp_path):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    request = build_extraction_request(normalized, ElicitationOutput(), config)
    replay = _seed(tmp_path, [(request, _valid_extraction_payload())])
    path = tmp_path / "topology.yaml"
    path.write_text(
        "topology_version: '1.0'\n"
        "provider_id: recorded@1\n"
        "task_kinds:\n"
        "  - extraction\n"
        "  - synthesis\n",
        encoding="utf-8",
    )
    local = LocalModelProvider.from_topology(replay, LocalTopology.load(path))
    assert local.declaration.provider_id == "recorded@1"
    assert local.declaration.locality is LocalityLevel.L2_LOCAL_MODEL
