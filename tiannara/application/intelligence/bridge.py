"""LanguageModelBridge — satisfies the Cap-B LanguageModelProvider port
through the AIR cascade.

Existing providers (B2 recorded replay, B6 live) are wrapped as model-class
IntelligenceProviders; Cap-B continues to receive the exact ModelCallRecord
the underlying provider produced, so B2/B5 provenance is byte-identical.
AIR adds the cascade, capability matching, and autonomy accounting around
them — nothing changes inside them.

D4 adds `complete_with_context`: it compiles a ContextGraph into a prompt via
PromptCompiler and routes that compiled prompt through the same cascade, so
context-aware requests gain deterministic, budget-governed provenance without
a new routing seam.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel

from tiannara.domain.models.context_graph import ContextGraph
from tiannara.domain.models.intelligence import (
    CapabilityDeclaration,
    IntelligenceResult,
    IntelligenceTask,
    PrivacyClass,
    ProviderClass,
    TaskKind,
)
from tiannara.domain.models.model_call import StructuredCompletionRequest
from tiannara.domain.ports.language_model import (
    LanguageModelProvider,
    StructuredCompletionResult,
)

from .cascade import CascadeExecutor
from .context_budgeter import TokenBudget
from .prompt_compiler import CompiledPrompt, PromptCompiler, TaskInstruction
from .router import RoutingPolicy

DEFAULT_TASK_KIND_MAP: dict[str, TaskKind] = {
    "intent.elicitation": TaskKind.EXTRACTION,
    "intent.repair": TaskKind.SYNTHESIS,
    "synthesis.render": TaskKind.SYNTHESIS,
}

OutputT = TypeVar("OutputT", bound=BaseModel)


class LanguageModelIntelligenceAdapter:
    """Wraps any LanguageModelProvider as an IntelligenceProvider."""

    def __init__(
        self,
        provider: LanguageModelProvider,
        declaration: CapabilityDeclaration,
    ) -> None:
        self._provider = provider
        self._declaration = declaration

    @property
    def declaration(self) -> CapabilityDeclaration:
        return self._declaration

    def complete(self, task: IntelligenceTask) -> IntelligenceResult:
        if task.output_type is None:
            raise ValueError("task.output_type is required for model adapters")
        request = StructuredCompletionRequest(
            model_id=task.model_hint or self._declaration.provider_id,
            task=task.task_label,
            prompt=task.prompt,
            output_schema_id=task.output_schema_id,
            decoding=task.decoding,
        )
        result = self._provider.complete_structured(request, task.output_type)
        return IntelligenceResult(
            output_payload=result.output.model_dump(mode="json"),
            provider_id=self._declaration.provider_id,
            provider_class=self._declaration.provider_class,
            locality=self._declaration.locality,
            model_record=result.record,
        )


class LanguageModelBridge:
    """Implements LanguageModelProvider over the AIR cascade."""

    def __init__(
        self,
        executor: CascadeExecutor,
        policy: RoutingPolicy,
        task_kind_map: dict[str, TaskKind] | None = None,
        privacy_class: PrivacyClass = PrivacyClass.INTERNAL,
        prompt_compiler: PromptCompiler | None = None,
        call_observer: Callable[[IntelligenceResult], None] | None = None,
    ) -> None:
        self._executor = executor
        self._policy = policy
        self._task_kind_map = task_kind_map or DEFAULT_TASK_KIND_MAP
        self._privacy_class = privacy_class
        self._prompt_compiler = prompt_compiler
        self._call_observer = call_observer

    def complete_structured(
        self,
        request: StructuredCompletionRequest,
        output_type: type[BaseModel],
    ) -> StructuredCompletionResult:
        task = IntelligenceTask(
            task_kind=self._task_kind_map.get(request.task, TaskKind.SYNTHESIS),
            task_label=request.task,
            prompt=request.prompt,
            output_schema_id=request.output_schema_id,
            decoding=request.decoding,
            model_hint=request.model_id,
            privacy_class=self._privacy_class,
            output_type=output_type,
        )
        result = self._executor.execute(task, self._policy)
        if self._call_observer is not None:
            self._call_observer(result)
        return StructuredCompletionResult(
            output=output_type.model_validate(result.output_payload),
            record=result.model_record,
        )

    def complete_with_context(
        self,
        request: StructuredCompletionRequest,
        output_type: type[OutputT],
        graph: ContextGraph,
        budget: TokenBudget,
        instruction: TaskInstruction,
    ) -> "ContextAwareCompletion[OutputT]":
        """Compile the context graph, then route the compiled prompt through
        the cascade. The graph's task_kind is authoritative; the incoming
        request supplies model/task/schema/decoding identity only — its prompt
        field is replaced by the compiled artifact.
        """
        compiler = self._prompt_compiler or PromptCompiler()
        compiled = compiler.compile(graph, budget, instruction)
        task = IntelligenceTask(
            task_kind=graph.task_kind,
            task_label=request.task,
            prompt=compiled.prompt,
            output_schema_id=request.output_schema_id,
            decoding=request.decoding,
            model_hint=request.model_id,
            subject_ref=graph.subject_ref or graph.graph_id,
            privacy_class=self._privacy_class,
            output_type=output_type,
        )
        outcome = self._executor.execute(task, self._policy)
        if self._call_observer is not None:
            self._call_observer(outcome)
        return ContextAwareCompletion(
            compiled_prompt=compiled,
            result=StructuredCompletionResult(
                output=output_type.model_validate(outcome.output_payload),
                record=outcome.model_record,
            ),
        )


@dataclass(frozen=True)
class ContextAwareCompletion(Generic[OutputT]):
    compiled_prompt: CompiledPrompt
    result: StructuredCompletionResult[OutputT]
