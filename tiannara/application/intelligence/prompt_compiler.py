"""PromptCompiler — deterministic compilation of prompts.

Pure L0 code: no model calls, no network, no wall-clock. Identical
(ContextGraph, TokenBudget, TaskInstruction, tokenizer) inputs always
produce a byte-identical CompiledPrompt.

Layout of the compiled artifact:

    ROLE / OBJECTIVE / CONSTRAINTS block
    ## CONTEXT            (selected nodes, original order)
    ## OUTPUT SCHEMA      (schema id + optional summary)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from tiannara.domain.models.context_graph import ContextGraph
from tiannara.domain.services.canonical import canonical_hash

from .context_budgeter import (
    InstructionOverflowError,
    MustContextOverflowError,
    SchemaOverflowError,
    TokenBudget,
    plan_context_selection,
)
from .tokenizing import CharRatioEstimator


class TaskInstruction(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    output_schema_id: str = Field(min_length=1)
    output_schema_summary: str = ""

    def render(self) -> str:
        lines = [f"ROLE: {self.role}", f"OBJECTIVE: {self.objective}"]
        if self.constraints:
            lines.append("CONSTRAINTS:")
            lines.extend(f"- {constraint}" for constraint in self.constraints)
        lines.append(
            f"Respond ONLY with JSON conforming to output schema "
            f"'{self.output_schema_id}'."
        )
        return "\n".join(lines)

    def render_schema_block(self) -> str:
        lines = [f"OUTPUT SCHEMA: {self.output_schema_id}"]
        if self.output_schema_summary:
            lines.append(self.output_schema_summary)
        return "\n".join(lines)


class CompiledPrompt(BaseModel):
    """A compiled prompt artifact with full provenance."""

    prompt: str
    graph_id: str
    graph_hash: str
    prompt_hash: str
    budget: TokenBudget
    tokenizer_name: str
    instruction_tokens: int
    schema_tokens: int
    context_tokens: int
    total_tokens: int
    included_node_ids: list[str] = Field(default_factory=list)
    dropped_node_ids: list[str] = Field(default_factory=list)

    def content_hash(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class PromptCompiler:
    def __init__(self, tokenizer: CharRatioEstimator | None = None) -> None:
        self._tokenizer = tokenizer or CharRatioEstimator()

    def compile(
        self,
        graph: ContextGraph,
        budget: TokenBudget,
        instruction: TaskInstruction,
    ) -> CompiledPrompt:
        tokenizer = self._tokenizer

        instruction_text = instruction.render()
        schema_text = instruction.render_schema_block()
        instruction_tokens = tokenizer.count(instruction_text)
        schema_tokens = tokenizer.count(schema_text)

        if instruction_tokens > budget.instruction_reserve_tokens:
            raise InstructionOverflowError(
                instruction_tokens, budget.instruction_reserve_tokens
            )
        if schema_tokens > budget.schema_reserve_tokens:
            raise SchemaOverflowError(schema_tokens, budget.schema_reserve_tokens)

        planning = plan_context_selection(
            graph.nodes, tokenizer, budget.context_pool_tokens
        )
        included = set(planning.included_node_ids)
        sections = [node.render() for node in graph.nodes if node.node_id in included]
        context_text = "\n\n".join(sections)

        parts = [instruction_text, "\n## CONTEXT\n"]
        if context_text:
            parts.append(context_text)
        parts.append("\n\n## OUTPUT SCHEMA\n")
        parts.append(schema_text)
        prompt = "".join(parts)

        total_tokens = tokenizer.count(prompt)
        if total_tokens > budget.total_tokens:
            raise ContextBudgetOverflow(total_tokens, budget.total_tokens)

        return CompiledPrompt(
            prompt=prompt,
            graph_id=graph.graph_id,
            graph_hash=graph.content_hash(),
            prompt_hash=canonical_hash(prompt),
            budget=budget,
            tokenizer_name=tokenizer.name,
            instruction_tokens=instruction_tokens,
            schema_tokens=schema_tokens,
            context_tokens=tokenizer.count(context_text),
            total_tokens=total_tokens,
            included_node_ids=planning.included_node_ids,
            dropped_node_ids=planning.dropped_node_ids,
        )


class ContextBudgetOverflow(Exception):
    def __init__(self, actual: int, limit: int) -> None:
        super().__init__(f"compiled prompt needs {actual} tokens; budget is {limit}")
