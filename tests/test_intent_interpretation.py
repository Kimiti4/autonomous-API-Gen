"""Specification-agnostic interpretation layer contract tests.

Covers the internal interpretation package (elicitation, extraction,
repair), its fail-closed behavior, and the InterpretingModelProvider port
adapter -- including the regression where ``normalize()`` collapses markdown
structure into a single line before interpretation sees the statement.
No fixture, transcript, or golden artifact is involved anywhere here.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from tiannara.application.intent import (
    IntentCompiler,
    IntentCompilerConfig,
    attempt_graph,
    normalize,
)
from tiannara.application.intent.interpretation import (
    InterpretationError,
    PromptStructureError,
    UninterpretableSpecificationError,
    interpret_elicitation,
    interpret_extraction,
    interpret_repair,
)
from tiannara.application.intent.interpretation.text import split_sections
from tiannara.application.intent.schemas import (
    DataSeed,
    EdgeSeed,
    ElicitationOutput,
    ExtractionOutput,
    FieldSeed,
    NodeSeed,
)
from tiannara.domain.models.model_call import StructuredCompletionRequest
from tiannara.infrastructure.llm.interpreting_provider import InterpretingModelProvider

TRIAL_DIR = Path(__file__).resolve().parents[1] / "experiments" / "taskflow-native"
PROBLEM = (TRIAL_DIR / "PROBLEM.md").read_text(encoding="utf-8")


def _load_run_trial():
    spec = importlib.util.spec_from_file_location(
        "taskflow_run_trial_for_interpretation", TRIAL_DIR / "run_trial.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _attempts(extraction: ExtractionOutput, limit: int = 6):
    current = extraction
    for _ in range(limit):
        graph, issues = attempt_graph(current, [], ["sig@test"], "hash@test")
        if graph is not None and not issues:
            return graph, current
        current = interpret_repair(current, issues)
    return None, current


# -- statement layout ---------------------------------------------------------


def test_split_sections_survives_normalize_collapsing_newlines():
    normalized = normalize(PROBLEM).normalized_statement
    assert "\n" not in normalized
    pairs = split_sections(normalized)
    behavior = [s for sec, s in pairs if "behavior" in sec.lower()]
    assert len(behavior) >= 8
    preamble = [
        s
        for sec, s in pairs
        if "behavior" not in sec.lower() and "notes" not in sec.lower()
    ]
    assert any("Tasks live in named lists" in s for s in preamble)
    assert any(s.startswith("Each task carries") for s in preamble)


# -- elicitation --------------------------------------------------------------


def test_elicitation_finds_capabilities_and_explicit_scope_assumptions():
    output = interpret_elicitation(normalize(PROBLEM))
    assert len(output.inferred_capabilities) >= 3
    assumption_text = " ".join(a.statement for a in output.assumptions)
    assert "small team" in assumption_text
    assert "per installation" in assumption_text
    assert "single maintainer" in assumption_text
    assert len(output.assumptions) >= 3
    assert isinstance(output.clarifications, list)


def test_elicitation_fails_closed_on_unanalyzable_statement():
    with pytest.raises(UninterpretableSpecificationError):
        interpret_elicitation(normalize("Do it."))
    with pytest.raises(InterpretationError):
        interpret_elicitation(normalize("Hmm."))


# -- extraction ---------------------------------------------------------------


def test_extraction_designs_task_and_list_entities_from_problem_statement():
    elicitation = interpret_elicitation(normalize(PROBLEM))
    extraction = interpret_extraction(normalize(PROBLEM), elicitation)

    models = {model.name: model for model in extraction.data_models}
    assert set(models) == {"task", "task_list"}

    fields = {field.name: field for field in models["task"].fields}
    assert fields["title"].type == "text" and fields["title"].required
    assert fields["notes"].type == "text" and not fields["notes"].required
    assert fields["status"].type == "enumeration"
    assert fields["status"].enumeration_values == ["open", "in_progress", "done"]
    assert fields["priority"].enumeration_values == ["low", "medium", "high"]
    assert fields["due_date"].type == "timestamp" and not fields["due_date"].required
    assert fields["list_id"].type == "reference" and not fields["list_id"].required
    assert "id" not in fields

    list_fields = {field.name: field for field in models["task_list"].fields}
    assert list_fields["name"].type == "text" and list_fields["name"].required

    kinds = [node.kind for node in extraction.nodes]
    assert kinds.count("functional") >= 3
    assert kinds.count("data") >= 2
    assert kinds.count("constraint") >= 2
    assert all(node.acceptance_criteria == [] for node in extraction.nodes)
    assert all(
        node.rationale.startswith("derived from source text")
        for node in extraction.nodes
    )
    assert all(edge.rationale for edge in extraction.edges)
    assert models["task"].owning_service_ref is not None
    assert models["task"].requirement_refs


def test_extraction_parses_enums_types_and_optional_fields():
    statement = (
        "Every order carries a status that starts at draft and can move to "
        "open or closed, a quantity, an optional note, and an amount in "
        "decimal currency.\n\n"
        "The browser page lists every order.\n"
    )
    extraction = interpret_extraction(normalize(statement), ElicitationOutput())
    model = next(m for m in extraction.data_models if m.name == "order")
    fields = {field.name: field for field in model.fields}
    assert fields["status"].type == "enumeration"
    assert fields["status"].enumeration_values == ["draft", "open", "closed"]
    assert fields["quantity"].type == "integer"
    assert fields["note"].type == "text" and not fields["note"].required
    assert fields["amount"].type == "decimal"


def test_extraction_parses_comma_separated_enum_lists_without_swallowing_fields():
    statement = (
        "Every parcel carries a category chosen from meals, travel, "
        "lodging or supplies, and an optional note.\n\n"
        "The browser page lists every parcel.\n"
    )
    extraction = interpret_extraction(normalize(statement), ElicitationOutput())
    model = next(m for m in extraction.data_models if m.name == "parcel")
    fields = {field.name: field for field in model.fields}
    assert set(fields) == {"category", "note"}
    assert fields["category"].type == "enumeration"
    assert fields["category"].enumeration_values == [
        "meals",
        "travel",
        "lodging",
        "supplies",
    ]
    assert fields["note"].type == "text" and not fields["note"].required

    statement = (
        "Every order carries a status that starts at draft and can move to "
        "submitted, approved or rejected, and an optional note.\n\n"
        "The browser page lists every order.\n"
    )
    extraction = interpret_extraction(normalize(statement), ElicitationOutput())
    model = next(m for m in extraction.data_models if m.name == "order")
    fields = {field.name: field for field in model.fields}
    assert set(fields) == {"status", "note"}
    assert fields["status"].enumeration_values == [
        "draft",
        "submitted",
        "approved",
        "rejected",
    ]
    assert fields["note"].type == "text" and not fields["note"].required


def test_extraction_derives_container_relation_into_child_reference():
    statement = "Every book has a title. Books live in named stacks."
    extraction = interpret_extraction(normalize(statement), ElicitationOutput())
    models = {model.name: model for model in extraction.data_models}
    assert set(models) == {"book", "book_stack"}
    book_fields = {field.name: field for field in models["book"].fields}
    assert book_fields["title"].type == "text"
    assert book_fields["stack_id"].type == "reference"
    assert not book_fields["stack_id"].required


def test_extraction_fails_closed_without_functional_requirements():
    with pytest.raises(UninterpretableSpecificationError):
        interpret_extraction(normalize("Do something vague."), ElicitationOutput())


def test_extracted_graph_passes_prevalidation_without_repair():
    extraction = interpret_extraction(
        normalize(PROBLEM), interpret_elicitation(normalize(PROBLEM))
    )
    graph, issues = attempt_graph(extraction, [], ["sig@test"], "hash@test")
    assert graph is not None
    assert issues == []


# -- repair -------------------------------------------------------------------


def test_repair_resolves_duplicate_nodes_dangling_edges_and_cycles():
    extraction = ExtractionOutput(
        nodes=[
            NodeSeed(ref="req-a", kind="functional", statement="Create things"),
            NodeSeed(ref="req-a", kind="functional", statement="Duplicate of a"),
            NodeSeed(ref="req-b", kind="functional", statement="List things"),
        ],
        edges=[
            EdgeSeed(
                source_ref="req-a", target_ref="req-b", kind="depends_on",
                rationale="a needs b",
            ),
            EdgeSeed(
                source_ref="req-b", target_ref="req-a", kind="depends_on",
                rationale="cycle",
            ),
            EdgeSeed(
                source_ref="req-a", target_ref="req-ghost", kind="depends_on",
                rationale="dangling",
            ),
        ],
    )
    graph, _current = _attempts(extraction)
    assert graph is not None
    assert graph.edges == []


def test_repair_maps_invalid_kind_and_priority():
    extraction = ExtractionOutput(
        nodes=[
            NodeSeed(
                ref="req-x", kind="hacked", statement="Do a thing",
                priority="urgent",
            )
        ],
        edges=[],
    )
    graph, _current = _attempts(extraction)
    assert graph is not None
    assert graph.nodes[0].kind.value == "unclassified"
    assert graph.nodes[0].priority.value == "must"


def test_repair_resolves_data_seed_issues():
    extraction = ExtractionOutput(
        nodes=[
            NodeSeed(ref="req-a", kind="functional", statement="Create records"),
            NodeSeed(ref="data-x", kind="data", statement="Records persist"),
        ],
        edges=[],
        data_models=[
            DataSeed(
                ref="data-x",
                name="widget",
                fields=[
                    FieldSeed(name="kind", type="str"),
                    FieldSeed(name="kind", type="text"),
                    FieldSeed(name="mode", type="enumeration"),
                ],
                owning_service_ref="req-ghost",
                requirement_refs=["req-nope"],
            ),
            DataSeed(
                ref="data-x",
                name="gear",
                fields=[FieldSeed(name="label", type="text")],
            ),
        ],
    )
    graph, current = _attempts(extraction)
    assert graph is not None
    assert len(current.data_models) == 1
    model = current.data_models[0]
    field_types = {field.name: field.type for field in model.fields}
    assert field_types == {"kind": "text", "mode": "text"}
    assert model.owning_service_ref is None
    assert model.requirement_refs == []


def test_repair_leaves_unrecognized_issues_for_the_bounded_loop():
    extraction = ExtractionOutput(
        nodes=[NodeSeed(ref="req-a", kind="functional", statement="Create things")],
        edges=[],
    )
    fixed = interpret_repair(extraction, ["something entirely unknown"])
    assert fixed.model_dump() == extraction.model_dump()


# -- provider -----------------------------------------------------------------


def _request(task: str, prompt: str) -> StructuredCompletionRequest:
    schema = {
        "intent.elicitation": "intent.elicitation.v1",
        "intent.extraction": "intent.extraction.v2",
        "intent.repair": "intent.repair.v2",
    }[task]
    return StructuredCompletionRequest(
        model_id="esap-interpreter@1",
        task=task,
        prompt=prompt,
        output_schema_id=schema,
    )


def test_provider_roundtrip_is_deterministic_and_provenanced():
    config = IntentCompilerConfig(model_id="esap-interpreter@1")
    provider = InterpretingModelProvider()
    first = IntentCompiler(provider, config).compile_full(
        PROBLEM, "sys-interpretation"
    )
    second = IntentCompiler(provider, config).compile_full(
        PROBLEM, "sys-interpretation"
    )
    assert first.isr.content_hash() == second.isr.content_hash()
    assert first.requirement_graph.content_hash() == second.requirement_graph.content_hash()
    assert first.repair_iterations == 0
    assert [record.model_id for record in first.call_records] == [
        "esap-interpreter@1",
        "esap-interpreter@1",
    ]
    for record in first.call_records:
        assert record.signature_hash
        assert record.prompt_hash
        assert record.response_hash
        assert record.output_payload


def test_provider_fails_closed_on_prompt_without_statement_marker():
    provider = InterpretingModelProvider()
    with pytest.raises(PromptStructureError):
        provider.complete_structured(
            _request("intent.elicitation", "no sections at all"),
            ElicitationOutput,
        )


def test_provider_fails_closed_on_missing_context_sections():
    provider = InterpretingModelProvider()
    extraction_prompt = "PROBLEM STATEMENT:\nEvery task has a title."
    with pytest.raises(PromptStructureError):
        provider.complete_structured(
            _request("intent.extraction", extraction_prompt),
            ExtractionOutput,
        )
    repair_prompt = (
        "PROBLEM STATEMENT:\nEvery task has a title.\n\n"
        "CURRENT GRAPH:\n{}\n\n"
    )
    with pytest.raises(PromptStructureError):
        provider.complete_structured(
            _request("intent.repair", repair_prompt),
            ExtractionOutput,
        )


def test_provider_fails_closed_on_unknown_task():
    provider = InterpretingModelProvider()
    request = StructuredCompletionRequest(
        model_id="esap-interpreter@1",
        task="intent.unknown",
        prompt="PROBLEM STATEMENT:\nNothing here.",
        output_schema_id="intent.unknown.v1",
    )
    with pytest.raises(PromptStructureError):
        provider.complete_structured(request, ElicitationOutput)


def test_provider_repair_task_applies_deterministic_fixes():
    from tiannara.application.intent import build_repair_request
    from tiannara.application.intent.config import IntentCompilerConfig as _Cfg

    config = _Cfg(model_id="esap-interpreter@1")
    current = ExtractionOutput(
        nodes=[
            NodeSeed(ref="req-a", kind="functional", statement="Create things"),
            NodeSeed(ref="req-a", kind="functional", statement="Duplicate"),
        ],
        edges=[],
    )
    issues = ["Value error, duplicate node ids: ['req-a']"]
    request = build_repair_request(normalize(PROBLEM), current, issues, 1, config)
    result = InterpretingModelProvider().complete_structured(
        request, ExtractionOutput
    )
    assert [node.ref for node in result.output.nodes] == ["req-a"]
    assert result.record.model_id == "esap-interpreter@1"
    assert result.record.task == "intent.repair"


# -- composition + trial wiring -----------------------------------------------


def test_composition_interpreted_mode_builds_project_compiler():
    from tiannara.application.compiler.composition import build_project_compiler

    compiler = build_project_compiler(provider_mode="interpreted")
    assert compiler is not None


def test_run_trial_graph_evidence_comes_from_the_interpreter():
    run_trial = _load_run_trial()
    graph_evidence, interpretation = run_trial.compile_for_graph_evidence(PROBLEM)
    assert graph_evidence["isr_hash"]
    assert graph_evidence["system_name"]
    assert graph_evidence["node_count"] >= 4
    assert graph_evidence["repair_iterations"] == 0
    assert interpretation["provider_model"] == "esap-interpreter@1"
    assert interpretation["statement_hash"]
    assert len(interpretation["calls"]) == 2
    payload = json.dumps(interpretation)
    assert "AC-01" not in payload
    assert "seed_transcript" not in payload
