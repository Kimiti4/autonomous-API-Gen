"""Token budgeting and priority-ordered context selection.

Rules:
  * MUST nodes are taken in original order and must fit whole, else
    compilation fails loudly;
  * SHOULD then COULD nodes are taken in original order while they fit;
  * every dropped node is recorded — budget pressure is evolutionary
    evidence, not silent loss.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tiannara.domain.models.context_graph import ContextNode
from tiannara.domain.models.system_model import Priority
from tiannara.domain.ports.tokenizer import TokenEstimator


class ContextBudgetError(ValueError):
    """Base error for budget violations."""


class MustContextOverflowError(ContextBudgetError):
    def __init__(self, node_id: str, required: int, available: int) -> None:
        self.node_id = node_id
        self.required = required
        self.available = available
        super().__init__(
            f"MUST context node '{node_id}' requires {required} tokens but "
            f"only {available} remain in the context pool"
        )


class InstructionOverflowError(ContextBudgetError):
    def __init__(self, required: int, reserve: int) -> None:
        self.required = required
        self.reserve = reserve
        super().__init__(
            f"instruction requires {required} tokens; reserve is {reserve}"
        )


class SchemaOverflowError(ContextBudgetError):
    def __init__(self, required: int, reserve: int) -> None:
        self.required = required
        self.reserve = reserve
        super().__init__(
            f"schema block requires {required} tokens; reserve is {reserve}"
        )


class TokenBudget(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_tokens: int = Field(gt=0)
    output_reserve_tokens: int = Field(ge=0)
    instruction_reserve_tokens: int = Field(ge=0)
    schema_reserve_tokens: int = Field(ge=0)

    @model_validator(mode="after")
    def _reserves_fit(self) -> "TokenBudget":
        reserved = (
            self.output_reserve_tokens
            + self.instruction_reserve_tokens
            + self.schema_reserve_tokens
        )
        if reserved >= self.total_tokens:
            raise ValueError(
                f"reserves ({reserved}) must be strictly less than "
                f"total_tokens ({self.total_tokens})"
            )
        return self

    @property
    def context_pool_tokens(self) -> int:
        return (
            self.total_tokens
            - self.output_reserve_tokens
            - self.instruction_reserve_tokens
            - self.schema_reserve_tokens
        )


class BudgetPlanning(BaseModel):
    included_node_ids: list[str] = Field(default_factory=list)
    dropped_node_ids: list[str] = Field(default_factory=list)
    section_tokens: dict[str, int] = Field(default_factory=dict)
    context_tokens_used: int = 0


def plan_context_selection(
    nodes: list[ContextNode],
    tokenizer: TokenEstimator,
    pool_tokens: int,
) -> BudgetPlanning:
    """Deterministic selection: MUST (all, in order), then SHOULD, then COULD.

    Rendering uses ContextNode.render() — the identical method the compiler
    uses for weaving — so counted sizes and woven text never diverge.
    """
    rendered_tokens: dict[str, int] = {
        node.node_id: tokenizer.count(node.render()) for node in nodes
    }
    included: list[str] = []
    dropped: list[str] = []
    used = 0

    must_nodes = [n for n in nodes if n.priority is Priority.MUST]
    for node in must_nodes:
        cost = rendered_tokens[node.node_id]
        if used + cost > pool_tokens:
            raise MustContextOverflowError(node.node_id, cost, pool_tokens - used)
        included.append(node.node_id)
        used += cost

    for priority in (Priority.SHOULD, Priority.COULD):
        for node in nodes:
            if node.priority is not priority:
                continue
            cost = rendered_tokens[node.node_id]
            if used + cost <= pool_tokens:
                included.append(node.node_id)
                used += cost
            else:
                dropped.append(node.node_id)

    return BudgetPlanning(
        included_node_ids=included,
        dropped_node_ids=dropped,
        section_tokens=rendered_tokens,
        context_tokens_used=used,
    )
