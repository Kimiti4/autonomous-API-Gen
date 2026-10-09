"""InterpretingModelProvider -- internal, deterministic interpretation adapter.

Implements the ``LanguageModelProvider`` port without any network, vendor,
fixture, or transcript: the "model" is the specification-agnostic rule set in
``tiannara.application.intent.interpretation``. Prompts built by
``application.intent.prompts`` are parsed structurally (marker sections), the
statement is interpreted, and a ``ModelCallRecord`` is constructed exactly
like recorded/replaying providers do -- so provenance, replay signatures, and
graph ``model_versions`` all keep working.

Fail-closed: missing prompt sections, malformed embedded JSON, or an
uninterpretable statement raise ``InterpretationError`` subtypes
(``LanguageModelError``); output is never fabricated.
"""

from __future__ import annotations

import json
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from tiannara.application.intent.interpretation import (
    InterpretationError,
    interpret_elicitation,
    interpret_extraction,
    interpret_repair,
)
from tiannara.application.intent.interpretation.errors import PromptStructureError
from tiannara.domain.models.model_call import (
    LanguageModelError,
    ModelCallRecord,
    ModelCallStatus,
    StructuredCompletionRequest,
    compute_call_signature,
    hash_payload,
    hash_prompt,
)
from tiannara.domain.ports.language_model import StructuredCompletionResult

OutputT = TypeVar("OutputT", bound=BaseModel)

_MODEL_ID = "esap-interpreter@1"

_STATEMENT_MARKER = "PROBLEM STATEMENT:\n"
_ELICITATION_MARKER = "\n\nELICITATION CONTEXT:\n"
_GRAPH_MARKER = "\n\nCURRENT GRAPH:\n"
_ISSUES_MARKER = "\n\nISSUES:\n"
_ITERATION_MARKER = "\n\nREPAIR ITERATION: "


def _section(prompt: str, start_marker: str, end_marker: str | None) -> str:
    if start_marker not in prompt:
        raise PromptStructureError(
            f"prompt is missing required section {start_marker!r}"
        )
    body = prompt.split(start_marker, 1)[1]
    if end_marker is not None:
        if end_marker not in body:
            raise PromptStructureError(
                f"prompt is missing required section {end_marker!r}"
            )
        body = body.split(end_marker, 1)[0]
    return body


def _parse_json(section: str, label: str) -> dict:
    try:
        payload = json.loads(section)
    except json.JSONDecodeError as exc:
        raise PromptStructureError(
            f"{label} section is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise PromptStructureError(f"{label} section is not a JSON object")
    return payload


def _parse_issues(section: str) -> list[str]:
    issues = [
        line[2:].strip()
        for line in section.splitlines()
        if line.strip().startswith("- ")
    ]
    if not issues:
        raise PromptStructureError("ISSUES section carried no issue lines")
    return issues


class InterpretingModelProvider:
    """Deterministic in-process interpretation behind the provider port."""

    model_id = _MODEL_ID

    def __init__(self, clock=time.perf_counter) -> None:
        self._clock = clock

    def complete_structured(
        self,
        request: StructuredCompletionRequest,
        output_type: type[OutputT],
    ) -> StructuredCompletionResult[OutputT]:
        start = self._clock()
        try:
            interpreted = self._interpret(request)
        except LanguageModelError:
            raise
        except Exception as exc:
            raise InterpretationError(
                f"interpretation failed for task {request.task!r}: {exc}"
            ) from exc

        payload = interpreted.model_dump(mode="json")
        try:
            output = output_type.model_validate(payload)
        except ValidationError as exc:
            raise PromptStructureError(
                f"interpreted output failed {output_type.__name__} "
                f"validation: {exc}"
            ) from exc

        payload_json = json.dumps(payload, sort_keys=True)
        record = ModelCallRecord(
            signature_hash=compute_call_signature(request),
            model_id=_MODEL_ID,
            task=request.task,
            output_schema_id=request.output_schema_id,
            prompt_hash=hash_prompt(request.prompt),
            response_hash=hash_payload(payload),
            output_payload=payload,
            input_tokens=max(1, len(request.prompt) // 4),
            output_tokens=max(1, len(payload_json) // 4),
            latency_ms=round((self._clock() - start) * 1000.0, 3),
            status=ModelCallStatus.LIVE,
            decoding=request.decoding,
        )
        return StructuredCompletionResult(output=output, record=record)

    def _interpret(self, request: StructuredCompletionRequest) -> BaseModel:
        from tiannara.application.intent.config import (
            INTENT_ELICITATION_TASK,
            INTENT_EXTRACTION_TASK,
            INTENT_REPAIR_TASK,
        )
        from tiannara.application.intent.prompts import normalize
        from tiannara.application.intent.schemas import (
            ElicitationOutput,
            ExtractionOutput,
        )

        prompt = request.prompt
        if request.task == INTENT_ELICITATION_TASK:
            statement = _section(prompt, _STATEMENT_MARKER, None)
            normalized = normalize(statement.strip())
            return interpret_elicitation(normalized)

        if request.task == INTENT_EXTRACTION_TASK:
            statement = _section(prompt, _STATEMENT_MARKER, _ELICITATION_MARKER)
            normalized = normalize(statement.strip())
            context = _section(prompt, _ELICITATION_MARKER, None)
            elicitation = ElicitationOutput.model_validate(
                _parse_json(context.strip(), "ELICITATION CONTEXT")
            )
            return interpret_extraction(normalized, elicitation)

        if request.task == INTENT_REPAIR_TASK:
            _section(prompt, _STATEMENT_MARKER, _GRAPH_MARKER)
            graph_section = _section(prompt, _GRAPH_MARKER, _ISSUES_MARKER)
            issues_section = _section(prompt, _ISSUES_MARKER, _ITERATION_MARKER)
            current = ExtractionOutput.model_validate(
                _parse_json(graph_section.strip(), "CURRENT GRAPH")
            )
            return interpret_repair(current, _parse_issues(issues_section))

        raise PromptStructureError(
            f"unknown interpretation task {request.task!r}"
        )
