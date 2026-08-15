"""Phase 19 -- select-all planning seam (additive over the single-best default).

Three guarantees exercised here, against the *real* typed IntentCompiler replayed
from a seeded transcript (same hermetic pattern as Phase 16):

  1. ``plan_compilation_across_backends`` yields one plan entry per matching
     backend (FastAPI + Go) for the same requirement.
  2. The DEFAULT planner ``plan_compilation`` is byte-for-byte unchanged: it
     still picks the single best backend (FastAPI, quality 0.85 > Go 0.80).
  3. ``compile_intent(..., plan_all=True)`` with a both-backends registry
     produces two independently-verified outcomes from the same ISR, while
     ``plan_all=False`` still yields one.
"""
from __future__ import annotations

from pathlib import Path

from tiannara.application.compiler.composition import (
    build_project_compiler,
    build_compiler_registry,
    fastapi_declaration,
)
from tiannara.application.compiler.derivation import derive_compilation_requirements
from tiannara.application.compiler.go_hexagonal_backend import GoHexagonalBackend
from tiannara.application.compiler.project_compiler import ProjectCompiler
from tiannara.application.compiler.selector import (
    DEFAULT_SELECTION_POLICY,
    plan_compilation,
    plan_compilation_across_backends,
)
from tiannara.application.intent.config import IntentCompilerConfig
from tiannara.application.intent.prompts import (
    build_elicitation_request,
    build_extraction_request,
    normalize,
)
from tiannara.application.intent.schemas import ElicitationOutput, ExtractionOutput
from tiannara.domain.models.backend_declaration import (
    BackendCapabilityDeclaration,
    CompilationRequirement,
)
from tiannara.domain.models.model_call import (
    ModelCallRecord,
    compute_call_signature,
    hash_payload,
)
from tiannara.domain.models.system_model import (
    RequirementsReference,
    ServiceSpec,
    SystemModel,
)
from tiannara.infrastructure.llm.transcript import ModelCallTranscript
from tiannara.infrastructure.source_control.in_memory import (
    InMemorySourceControlBackend,
)

STATEMENT = "Order Management"

_ELICITATION = {
    "inferred_capabilities": ["Order Processing"],
    "assumptions": [{"statement": "Clients place orders online"}],
    "clarifications": ["Payment provider"],
}
_EXTRACTION = {
    "nodes": [
        {"ref": "req-order", "kind": "functional", "statement": "Process orders", "priority": "must"}
    ],
    "edges": [],
}


def _record(request, payload):
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
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation = ElicitationOutput(**_ELICITATION)
    path = tmp_path / "transcript.jsonl"
    transcript = ModelCallTranscript(path)
    transcript.append(_record(build_elicitation_request(normalized, config), _ELICITATION))
    transcript.append(
        _record(build_extraction_request(normalized, elicitation, config), _EXTRACTION)
    )
    return path


def _both_registry():
    reg = build_compiler_registry()  # FastAPI only (default)
    go = GoHexagonalBackend()
    reg.register(go, go.build_profile_declaration())
    return reg


def _service_requirement() -> CompilationRequirement:
    sm = SystemModel(
        system_name="Order Management",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        services=[ServiceSpec(id="svc-1", name="order", domain_id="general")],
    )
    reqs = derive_compilation_requirements(sm)
    assert len(reqs) == 1
    return reqs[0]


def test_select_all_yields_one_plan_entry_per_backend():
    reg = _both_registry()
    req = _service_requirement()
    plan = plan_compilation_across_backends(reg, [req], DEFAULT_SELECTION_POLICY)
    ids = {p.backend_id for p in plan.planned}
    assert ids == {"fastapi_hexagonal", "go_hexagonal"}
    assert len(plan.planned) == 2


def test_default_planner_still_single_best():
    reg = _both_registry()
    req = _service_requirement()
    plan = plan_compilation(reg, [req], DEFAULT_SELECTION_POLICY)
    assert len(plan.planned) == 1
    # FastAPI quality 0.85 > Go 0.80 -> default picks FastAPI.
    assert plan.planned[0].backend_id == "fastapi_hexagonal"


def test_compile_intent_plan_all_compiles_same_isr_to_both_backends(tmp_path):
    transcript = _seed_transcript(tmp_path)
    compiler = build_project_compiler(
        "recorded",
        transcript_path=transcript,
        registry=_both_registry(),
        plan_all=True,
    )
    report = compiler.compile_intent(STATEMENT, {})

    assert report.ok is True
    assert len(report.outcomes) == 2
    by_id = {o.planned.backend_id: o for o in report.outcomes}
    assert set(by_id) == {"fastapi_hexagonal", "go_hexagonal"}
    for outcome in report.outcomes:
        assert outcome.status == "success"
        assert outcome.verification_report is not None
        assert outcome.verification_report.ok is True
        assert outcome.verification_reason == ""

    fastapi_files = set(by_id["fastapi_hexagonal"].result.files)
    go_files = set(by_id["go_hexagonal"].result.files)
    # Distinct file schemas: Go module-rooted, FastAPI slug-rooted.
    assert "go.mod" in go_files and "go.mod" not in fastapi_files
    assert "cmd/server/main.go" in go_files
    assert "order_management/main.py" in fastapi_files
    # Both emitted a container contract (Dockerfile) -- collision-free at the
    # report level; materialization namespacing is a Phase-31 concern.
    assert "Dockerfile" in fastapi_files and "Dockerfile" in go_files


def test_compile_intent_default_plan_is_single_backend(tmp_path):
    transcript = _seed_transcript(tmp_path)
    compiler = build_project_compiler(
        "recorded",
        transcript_path=transcript,
        registry=_both_registry(),
        plan_all=False,
    )
    report = compiler.compile_intent(STATEMENT, {})
    assert report.ok is True
    assert len(report.outcomes) == 1
    assert report.outcomes[0].planned.backend_id == "fastapi_hexagonal"
    assert isinstance(compiler, ProjectCompiler)
