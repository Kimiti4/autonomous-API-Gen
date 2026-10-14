from pathlib import Path

import pytest

from tiannara.application.intent import (
    IntentCompiler,
    IntentCompilerConfig,
    RepairBudgetExceeded,
    attempt_graph,
    build_elicitation_request,
    build_extraction_request,
    build_repair_request,
    normalize,
)
from tiannara.application.intent.schemas import ElicitationOutput, ExtractionOutput, TaskFlowSemanticProjection
from tiannara.domain.models.system_model import RequirementsReference, SystemModel
from tiannara.domain.models.model_call import (
    ModelCallRecord,
    ModelCallStatus,
    compute_call_signature,
    hash_payload,
)
from tiannara.domain.models.system_model import TechnologyCouplingError
from tiannara.domain.models.taskflow_semantic_contract import REQUIRED_VALUE_SHAPES
from tiannara.domain.models.semantic_resolution import (
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
    TASKFLOW_MANDATORY_FIELDS,
    UnresolvedSemanticsError,
)
from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
from tiannara.infrastructure.llm.recording_provider import RecordingModelProvider
from tiannara.infrastructure.llm.transcript import ModelCallTranscript

STATEMENT = "We need a system to book berths at marinas and track availability."


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


def _elicitation_payload(capabilities=None, assumptions=None):
    return {
        "inferred_capabilities": capabilities or ["berth booking"],
        "assumptions": assumptions
        or [{"statement": "Marinas manage their own berths", "rationale": "typical"}],
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


def test_happy_path_records_and_provenance(tmp_path):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload()
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    extraction_payload = _valid_extraction_payload()

    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), extraction_payload),
        ],
    )
    compiler = IntentCompiler(provider, config)
    result = compiler.compile_full(STATEMENT, system_id="sys-1")

    assert result.repair_iterations == 0
    assert len(result.call_records) == 2
    assert all(r.status is ModelCallStatus.REPLAYED for r in result.call_records)
    assert len(result.requirement_graph.provenance.model_versions) == 2
    assert result.requirement_graph.provenance.model_versions[0].startswith("recorded@1:")
    node_ids = {n.id for n in result.requirement_graph.nodes}
    assert {"req-book", "req-avail", "asm-1"} <= node_ids
    assert result.assumption_ids == ["asm-1"]
    assert result.isr.system_model() is not None



def test_source_graph_provenance_mismatch_blocks_before_synthesis(tmp_path, monkeypatch):
    import tiannara.application.intent.compiler as compiler_module

    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload()
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), _valid_extraction_payload()),
        ],
    )
    original_attempt_graph = compiler_module.attempt_graph

    def substituted_graph(*args, **kwargs):
        graph, issues = original_attempt_graph(*args, **kwargs)
        if graph is not None:
            graph.provenance.source_statement_hash = "0" * 64
        return graph, issues

    monkeypatch.setattr(compiler_module, "attempt_graph", substituted_graph)
    compiler = IntentCompiler(provider, config)
    with pytest.raises(ValueError, match="source provenance does not match"):
        compiler.compile_full(STATEMENT, system_id="source-provenance-mismatch")

def test_repair_converges_in_one_iteration(tmp_path):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload(assumptions=[])
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)

    invalid_payload = {
        "nodes": [
            {"ref": "req-book", "kind": "functional", "statement": "Book a berth", "priority": "must"}
        ],
        "edges": [
            {"source_ref": "req-book", "target_ref": "ghost", "kind": "refines"}
        ],
    }
    invalid_out = ExtractionOutput.model_validate(invalid_payload)
    _, issues = attempt_graph(invalid_out, [], [], normalized.source_statement_hash)
    assert issues

    valid_repair_payload = _valid_extraction_payload()
    valid_repair_payload["changes_summary"] = "removed dangling edge"

    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), invalid_payload),
            (build_repair_request(normalized, invalid_out, issues, 1, config), valid_repair_payload),
        ],
    )
    compiler = IntentCompiler(provider, config)
    result = compiler.compile_full(STATEMENT, system_id="sys-2")
    assert result.repair_iterations == 1
    assert len(result.call_records) == 3


def test_repair_diverges_and_raises(tmp_path):
    config = IntentCompilerConfig()  # max_repair_iterations = 3
    normalized = normalize(STATEMENT)
    src = normalized.source_statement_hash
    elicitation_payload = _elicitation_payload(assumptions=[])
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)

    invalid_payload = {
        "nodes": [
            {"ref": "req-book", "kind": "functional", "statement": "Book", "priority": "must"}
        ],
        "edges": [
            {"source_ref": "req-book", "target_ref": "ghost", "kind": "refines"}
        ],
    }
    invalid_out = ExtractionOutput.model_validate(invalid_payload)
    _, issues = attempt_graph(invalid_out, [], [], src)
    assert issues, "expected the invalid graph to produce issues"

    entries = [
        (build_elicitation_request(normalized, config), elicitation_payload),
        (build_extraction_request(normalized, elicitation_out, config), invalid_payload),
    ]
    for iteration in range(1, config.max_repair_iterations + 1):
        entries.append(
            (
                build_repair_request(normalized, invalid_out, issues, iteration, config),
                invalid_payload,
            )
        )

    replay = _seed(tmp_path, entries)
    transcript = ModelCallTranscript(tmp_path / "recorded.jsonl")
    provider = RecordingModelProvider(replay, transcript)
    compiler = IntentCompiler(provider, config)

    with pytest.raises(RepairBudgetExceeded) as exc:
        compiler.compile_full(STATEMENT, system_id="sys-3")
    assert exc.value.iterations == config.max_repair_iterations

    recorded = list(transcript.iter_records())
    assert len(recorded) == 1 + 1 + config.max_repair_iterations
    assert transcript.verify_chain() is True


def test_technology_boundary_enforced(tmp_path):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload(capabilities=["kafka streaming"], assumptions=[])
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    extraction_payload = _valid_extraction_payload()

    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), extraction_payload),
        ],
    )
    compiler = IntentCompiler(provider, config)
    with pytest.raises(TechnologyCouplingError):
        compiler.compile_full(STATEMENT, system_id="sys-4")


def test_deterministic_across_runs(tmp_path):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload()
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    extraction_payload = _valid_extraction_payload()

    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), extraction_payload),
        ],
    )
    compiler = IntentCompiler(provider, config)
    first = compiler.compile_full(STATEMENT, system_id="sys-5")
    second = compiler.compile_full(STATEMENT, system_id="sys-5")
    assert first.isr.content_hash() == second.isr.content_hash()
    assert first.requirement_graph.content_hash() == second.requirement_graph.content_hash()


@pytest.mark.parametrize("entrypoint", ["compile", "compile_full"])
def test_taskflow_scoped_compiler_cannot_bypass_gate(tmp_path, monkeypatch, entrypoint):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload()
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), _valid_extraction_payload()),
        ],
    )

    def forbidden_synthesis(*args, **kwargs):
        raise AssertionError("SystemModel synthesis must not run before semantic resolution")

    monkeypatch.setattr(
        "tiannara.application.intent.compiler.synthesize_system_model",
        forbidden_synthesis,
    )
    compiler = IntentCompiler(
        provider,
        config,
        taskflow_semantic_gate_required=True,
    )

    with pytest.raises(UnresolvedSemanticsError):
        if entrypoint == "compile":
            # The port-compatible entry point must preserve the instance policy.
            compiler.compile(STATEMENT, {})
        else:
            # An explicit False must not downgrade a TaskFlow-scoped compiler.
            compiler.compile_full(
                STATEMENT,
                system_id="taskflow-gate-bypass-attempt",
                taskflow_semantic_gate=False,
            )


def test_taskflow_semantic_gate_blocks_before_system_model_synthesis(tmp_path, monkeypatch):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload()
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    extraction_payload = _valid_extraction_payload()
    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), extraction_payload),
        ],
    )

    def forbidden_synthesis(*args, **kwargs):
        raise AssertionError("SystemModel synthesis must not run with unresolved semantics")

    monkeypatch.setattr(
        "tiannara.application.intent.compiler.synthesize_system_model",
        forbidden_synthesis,
    )
    compiler = IntentCompiler(provider, config)
    with pytest.raises(UnresolvedSemanticsError):
        compiler.compile_full(
            STATEMENT,
            system_id="taskflow-gated",
            taskflow_semantic_gate=True,
        )


def test_resolved_taskflow_ledger_still_blocks_without_semantic_projection(tmp_path):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload()
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    extraction_payload = _valid_extraction_payload()
    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), extraction_payload),
        ],
    )

    def reviewed_ledger(graph, initial):
        return SemanticResolutionRecord(
            graph_id=graph.graph_id,
            graph_hash=graph.content_hash(),
            required_fields=TASKFLOW_MANDATORY_FIELDS,
            resolutions=tuple(
                SemanticResolution(
                    field_path=path,
                    kind=ResolutionKind.SNAPSHOT,
                    value={key: ([{"fixture_value": True}] if shape == "array" else {"fixture_value": True}) for key, shape in REQUIRED_VALUE_SHAPES[path].items()},
                    source="test:reviewed-fixture",
                )
                for path in TASKFLOW_MANDATORY_FIELDS
            ),
        )

    compiler = IntentCompiler(provider, config, taskflow_semantic_resolver=reviewed_ledger)
    with pytest.raises(ValueError, match="semantic projection is not configured"):
        compiler.compile_full(
            STATEMENT,
            system_id="taskflow-projection-required",
            taskflow_semantic_gate=True,
        )



def _taskflow_reviewed_ledger(graph, _initial):
    return SemanticResolutionRecord(
        graph_id=graph.graph_id,
        graph_hash=graph.content_hash(),
        required_fields=TASKFLOW_MANDATORY_FIELDS,
        resolutions=tuple(
            SemanticResolution(
                field_path=path,
                kind=ResolutionKind.SNAPSHOT,
                value={
                    key: ([{"fixture_value": True}] if shape == "array" else {"fixture_value": True})
                    for key, shape in REQUIRED_VALUE_SHAPES[path].items()
                },
                source="test:reviewed-fixture",
            )
            for path in TASKFLOW_MANDATORY_FIELDS
        ),
    )


def _taskflow_projection(values, graph):
    model = SystemModel(
        system_name="taskflow-test",
        problem_statement="TaskFlow semantic projection test",
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id,
            graph_hash=graph.content_hash(),
        ),
        extensions={"taskflow_semantic_values": values},
    )
    return TaskFlowSemanticProjection(system_model=model, projected_values=values)


def test_taskflow_projection_must_cover_all_mandatory_fields(tmp_path):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload()
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), _valid_extraction_payload()),
        ],
    )

    def incomplete_projector(graph, _elicitation, _normalized, record):
        values = {record.required_fields[0]: record.resolutions[0].value}
        return _taskflow_projection(values, graph)

    compiler = IntentCompiler(
        provider,
        config,
        taskflow_semantic_resolver=_taskflow_reviewed_ledger,
        taskflow_semantic_projector=incomplete_projector,
    )
    with pytest.raises(ValueError, match="projection coverage mismatch"):
        compiler.compile_full(
            STATEMENT,
            system_id="taskflow-incomplete-projection",
            taskflow_semantic_gate=True,
        )


def test_taskflow_projection_cannot_change_reviewed_values(tmp_path):
    config = IntentCompilerConfig()
    normalized = normalize(STATEMENT)
    elicitation_payload = _elicitation_payload()
    elicitation_out = ElicitationOutput.model_validate(elicitation_payload)
    provider = _seed(
        tmp_path,
        [
            (build_elicitation_request(normalized, config), elicitation_payload),
            (build_extraction_request(normalized, elicitation_out, config), _valid_extraction_payload()),
        ],
    )

    def altered_projector(graph, _elicitation, _normalized, record):
        values = {item.field_path: item.value for item in record.resolutions}
        values["authorization.workspace_membership_scope"] = {
            "scoped_resources": [{"fixture_value": "weakened"}],
            "scoped_operations": [{"fixture_value": True}],
            "cross_scope_denial": {"fixture_value": True},
        }
        return _taskflow_projection(values, graph)

    compiler = IntentCompiler(
        provider,
        config,
        taskflow_semantic_resolver=_taskflow_reviewed_ledger,
        taskflow_semantic_projector=altered_projector,
    )
    with pytest.raises(ValueError, match="changed or omitted reviewed values"):
        compiler.compile_full(
            STATEMENT,
            system_id="taskflow-altered-projection",
            taskflow_semantic_gate=True,
        )
