"""Phase 16 -- composition root hermetic end-to-end.

Exercises the REAL typed IntentCompiler (Cap-A) front-end against a hermetic
RecordedModelProvider fed from a transcript, composed through the Phase 16
CLI composition root. There is no stub intent compiler here: the elicitation
and extraction stages of real ``IntentCompiler.compile`` request their
structured outputs from the recorded provider.

The transcript is seeded using the *same* deterministic prompt builders
(``build_elicitation_request`` / ``build_extraction_request``) and the same
``IntentCompilerConfig`` defaults that the real compiler uses, so the recorded
call signatures match byte-for-byte during replay -- no fabrication, no
network, no environment drift.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tiannara.application.compiler.composition import (
    CompositionError,
    build_project_compiler,
)
from tiannara.application.compiler.project_compiler import ProjectCompilationReport
from tiannara.application.compiler.writer import write_bundle
from tiannara.application.intent.config import IntentCompilerConfig
from tiannara.application.intent.prompts import (
    build_elicitation_request,
    build_extraction_request,
    normalize,
)
from tiannara.application.intent.schemas import ElicitationOutput, ExtractionOutput
from tiannara.domain.models.model_call import (
    ModelCallRecord,
    compute_call_signature,
    hash_payload,
)
from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
from tiannara.infrastructure.llm.transcript import ModelCallTranscript

STATEMENT = "Order Management"

_ELICITATION: dict = {
    "inferred_capabilities": ["Order Processing"],
    "assumptions": [{"statement": "Customers place orders online"}],
    "clarifications": ["Payment provider"],
}

_EXTRACTION: dict = {
    "nodes": [
        {
            "ref": "req-order",
            "kind": "functional",
            "statement": "Process customer orders",
            "priority": "must",
        }
    ],
    "edges": [],
}


def _record(request, payload: dict) -> ModelCallRecord:
    """Build a ModelCallRecord exactly as the real compiler will request it."""
    return ModelCallRecord(
        signature_hash=compute_call_signature(request),
        model_id=request.model_id,
        task=request.task,
        output_schema_id=request.output_schema_id,
        output_payload=payload,
        response_hash=hash_payload(payload),
        decoding=request.decoding,
    )


def _seed_transcript(tmp_path: Path) -> Path:
    """Commit a minimal, schema-valid elicitation+extraction transcript."""
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation = ElicitationOutput(**_ELICITATION)
    transcript_path = tmp_path / "transcript.jsonl"
    transcript = ModelCallTranscript(transcript_path)
    transcript.append(
        _record(build_elicitation_request(normalized, config), _ELICITATION)
    )
    transcript.append(
        _record(
            build_extraction_request(normalized, elicitation, config),
            _EXTRACTION,
        )
    )
    return transcript_path


def test_real_intent_compiler_replays_and_produces_verified_bundle(tmp_path):
    """Full Cap-A -> Cap-C path through the real IntentCompiler with replay."""
    transcript_path = _seed_transcript(tmp_path)
    compiler = build_project_compiler("recorded", transcript_path=transcript_path)

    report = compiler.compile_intent(STATEMENT, {})

    assert isinstance(report, ProjectCompilationReport)
    assert report.ok is True
    assert report.plan_id
    assert report.isr_hash
    assert len(report.outcomes) == 1

    outcome = report.outcomes[0]
    assert outcome.status == "success"
    assert outcome.error is None
    assert outcome.verification_report is not None
    assert outcome.verification_report.ok is True
    assert outcome.verification_reason == ""

    out_dir = tmp_path / "out"
    write_bundle(outcome.result, out_dir)
    slug = outcome.result.system_name
    assert (out_dir / slug / "main.py").exists()
    assert (out_dir / "Dockerfile").exists()


def test_real_intent_compiler_replay_signatures_are_byte_stable(tmp_path):
    """Replay returns the exact recorded payloads (no fabrication)."""
    transcript_path = _seed_transcript(tmp_path)
    provider = RecordedModelProvider(ModelCallTranscript(transcript_path))
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation = provider.complete_structured(
        build_elicitation_request(normalized, config), ElicitationOutput
    )
    assert elicitation.output.model_dump(mode="json")["inferred_capabilities"] == [
        "Order Processing"
    ]
    extraction = provider.complete_structured(
        build_extraction_request(normalized, elicitation.output, config),
        ExtractionOutput,
    )
    assert extraction.output.nodes[0].kind == "functional"


def test_recorded_mode_requires_transcript():
    with pytest.raises(CompositionError):
        build_project_compiler("recorded")


def test_live_mode_not_configured():
    with pytest.raises(CompositionError):
        build_project_compiler("live")


def test_unknown_provider_mode_rejected():
    with pytest.raises(CompositionError):
        build_project_compiler("wasm")


def test_explicit_provider_short_circuits_mode(tmp_path):
    transcript_path = _seed_transcript(tmp_path)
    provider = RecordedModelProvider(ModelCallTranscript(transcript_path))
    compiler = build_project_compiler(provider=provider)
    report = compiler.compile_intent(STATEMENT, {})
    assert report.ok is True
