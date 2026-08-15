"""D4: PromptCompiler - deterministic, budget-governed prompt compilation."""
import pytest

from tiannara.application.intelligence import (
    CompiledPrompt,
    InstructionOverflowError,
    PromptCompiler,
    SchemaOverflowError,
    TaskInstruction,
    TokenBudget,
)
from tiannara.application.intelligence.context_budgeter import ContextBudgetError
from tiannara.application.intelligence.tokenizing import (
    CharRatioEstimator,
    WhitespaceEstimator,
)
from tiannara.domain.models.context_graph import ContextGraph, ContextKind, ContextNode
from tiannara.domain.models.intelligence import TaskKind
from tiannara.domain.models.system_model import Priority


def _instruction():
    return TaskInstruction(
        role="Requirements Analyst agent",
        objective="Extract the requirement graph from the context.",
        constraints=["Use only the provided context.", "Make assumptions explicit."],
        output_schema_id="intent.extraction.v1",
        output_schema_summary="nodes: list[NodeSeed]; edges: list[EdgeSeed]",
    )


def _graph():
    nodes = [
        ContextNode(
            node_id="m1",
            kind=ContextKind.SECURITY_POSTURE,
            priority=Priority.MUST,
            title="Security",
            payload={"authentication": "token_based"},
        ),
        ContextNode(
            node_id="s1",
            kind=ContextKind.CAPABILITY,
            priority=Priority.SHOULD,
            title="Booking",
            payload={"name": "berth booking"},
        ),
    ]
    return ContextGraph.derive(TaskKind.EXTRACTION, nodes, subject_ref="m1")


def _budget():
    return TokenBudget(
        total_tokens=2000, output_reserve_tokens=400,
        instruction_reserve_tokens=300, schema_reserve_tokens=150,
    )


def test_compilation_is_byte_identical():
    compiler_a = PromptCompiler(CharRatioEstimator())
    compiler_b = PromptCompiler(CharRatioEstimator())
    first = compiler_a.compile(_graph(), _budget(), _instruction())
    second = compiler_b.compile(_graph(), _budget(), _instruction())
    assert first.prompt == second.prompt
    assert first.content_hash() == second.content_hash()
    assert first.prompt_hash == second.prompt_hash


def test_compiled_layout_contains_all_blocks():
    compiled = PromptCompiler().compile(_graph(), _budget(), _instruction())
    assert compiled.prompt.startswith("ROLE: Requirements Analyst agent")
    assert "## CONTEXT" in compiled.prompt
    assert "## OUTPUT SCHEMA" in compiled.prompt
    assert "intent.extraction.v1" in compiled.prompt
    assert compiled.included_node_ids == ["m1", "s1"]
    assert compiled.dropped_node_ids == []
    assert compiled.total_tokens <= 2000


def test_instruction_overflow_fails_loudly():
    tight = TokenBudget(
        total_tokens=2000, output_reserve_tokens=400,
        instruction_reserve_tokens=5, schema_reserve_tokens=150,
    )
    with pytest.raises(InstructionOverflowError):
        PromptCompiler().compile(_graph(), tight, _instruction())


def test_schema_overflow_fails_loudly():
    tight = TokenBudget(
        total_tokens=2000, output_reserve_tokens=400,
        instruction_reserve_tokens=300, schema_reserve_tokens=2,
    )
    with pytest.raises(SchemaOverflowError):
        PromptCompiler().compile(_graph(), tight, _instruction())


def test_budget_pressure_drops_should_and_records_it():
    estimator = CharRatioEstimator()
    must = ContextNode(
        node_id="m1", kind=ContextKind.SECURITY_POSTURE,
        priority=Priority.MUST, title="Security", payload={"a": 1},
    )
    should_big = ContextNode(
        node_id="s1", kind=ContextKind.CAPABILITY,
        priority=Priority.SHOULD, title="Big", payload={"blob": "y" * 800},
    )
    must_tokens = estimator.count(must.render())
    big_tokens = estimator.count(should_big.render())
    assert big_tokens > must_tokens  # sanity: the SHOULD node is genuinely large

    # Pool sized so MUST fits whole but the large SHOULD node cannot.
    pool = must_tokens + 1
    budget = TokenBudget(
        total_tokens=pool + 950,
        output_reserve_tokens=500,
        instruction_reserve_tokens=300,
        schema_reserve_tokens=150,
    )
    graph = ContextGraph.derive(TaskKind.EXTRACTION, [must, should_big])
    compiled = PromptCompiler(estimator).compile(graph, budget, _instruction())
    assert compiled.included_node_ids == ["m1"]
    assert compiled.dropped_node_ids == ["s1"]
    assert compiled.total_tokens <= budget.total_tokens


def test_tokenizer_identity_is_provenance():
    graph, budget, instruction = _graph(), _budget(), _instruction()
    char_compiled = PromptCompiler(CharRatioEstimator()).compile(graph, budget, instruction)
    word_compiled = PromptCompiler(WhitespaceEstimator()).compile(graph, budget, instruction)
    assert char_compiled.tokenizer_name == "char_ratio_4"
    assert word_compiled.tokenizer_name == "whitespace_punct"
    assert char_compiled.content_hash() != word_compiled.content_hash()
