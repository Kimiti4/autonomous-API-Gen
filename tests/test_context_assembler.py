"""D4: ContextAssembler - ISR slicing, evidence sourcing, end-to-end compile."""
from pathlib import Path

from tiannara.application.intelligence import (
    ContextAssembler,
    IsrContextExtractor,
    PromptCompiler,
    StaticEvidenceSource,
    TaskInstruction,
    TokenBudget,
)
from tiannara.domain.models.context_graph import ContextKind
from tiannara.domain.models.intelligence import TaskKind
from tiannara.domain.models.system_model import (
    BusinessCapability,
    Priority,
    RequirementsReference,
    ServiceSpec,
    SystemModel,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SEED_EVIDENCE = REPO_ROOT / "config" / "evidence" / "architectural_patterns.jsonl"


def _model():
    return SystemModel(
        system_name="harbor-ops",
        problem_statement="Track berth occupancy across marinas.",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        capabilities=[
            BusinessCapability(id="cap-1", name="Berth booking", traced_requirement_ids=["r1"]),
            BusinessCapability(id="cap-2", name="Availability reporting", traced_requirement_ids=["r2"]),
        ],
        services=[ServiceSpec(id="svc-1", name="core-service", domain_id="domain-core")],
    )


def test_static_evidence_source_filters_and_orders():
    source = StaticEvidenceSource.from_jsonl(SEED_EVIDENCE)
    results = source.query(TaskKind.SYNTHESIS, limit=10)
    assert [f.fragment_id for f in results] == ["ev-001", "ev-002", "ev-003"]
    extraction = source.query(TaskKind.EXTRACTION, limit=10)
    assert "ev-003" in [f.fragment_id for f in extraction]  # empty task_kinds = all
    limited = source.query(TaskKind.SYNTHESIS, limit=1)
    assert [f.fragment_id for f in limited] == ["ev-001"]


def test_isr_extractor_focus_semantics():
    extractor = IsrContextExtractor()
    unfocused = {n.node_id: n.priority for n in extractor.extract(_model())}
    assert unfocused["isr-security"] is Priority.MUST
    assert unfocused["isr-cap-cap-1"] is Priority.MUST
    assert unfocused["isr-cap-cap-2"] is Priority.MUST

    focused = {n.node_id: n.priority for n in extractor.extract(_model(), "cap-2")}
    assert focused["isr-cap-cap-2"] is Priority.MUST
    assert focused["isr-cap-cap-1"] is Priority.SHOULD
    assert focused["isr-svc-svc-1"] is Priority.COULD


def test_assemble_and_compile_end_to_end_deterministic():
    assembler = ContextAssembler(evidence_source=StaticEvidenceSource.from_jsonl(SEED_EVIDENCE))
    instruction = TaskInstruction(
        role="Requirements Analyst agent",
        objective="Extract requirements for the focused capability.",
        output_schema_id="intent.extraction.v1",
    )
    budget = TokenBudget(
        total_tokens=6000, output_reserve_tokens=800,
        instruction_reserve_tokens=400, schema_reserve_tokens=200,
    )

    graph_a = assembler.assemble_graph(TaskKind.EXTRACTION, isr=_model(),
                                       subject_ref="cap-2", evidence_limit=2)
    graph_b = assembler.assemble_graph(TaskKind.EXTRACTION, isr=_model(),
                                       subject_ref="cap-2", evidence_limit=2)
    assert graph_a.graph_id == graph_b.graph_id

    compiled_a = PromptCompiler().compile(graph_a, budget, instruction)
    compiled_b = PromptCompiler().compile(graph_b, budget, instruction)
    assert compiled_a.prompt == compiled_b.prompt
    assert "Berth booking" in compiled_a.prompt or "Availability reporting" in compiled_a.prompt
    assert "isr-security" in compiled_a.included_node_ids
