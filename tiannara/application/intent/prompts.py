"""Deterministic normalization and request construction.

Every prompt is a pure function of its inputs, using canonical JSON for any
embedded structure, so call signatures are reproducible and recorded fixtures
match exactly during replay.
"""

from __future__ import annotations

from tiannara.domain.models.model_call import StructuredCompletionRequest
from tiannara.domain.services.canonical import canonical_hash, canonical_json

from .config import (
    INTENT_ELICITATION_SCHEMA,
    INTENT_ELICITATION_TASK,
    INTENT_EXTRACTION_SCHEMA,
    INTENT_EXTRACTION_TASK,
    INTENT_REPAIR_SCHEMA,
    INTENT_REPAIR_TASK,
    IntentCompilerConfig,
)
from .schemas import ElicitationOutput, NormalizedIntent


def normalize(statement: str) -> NormalizedIntent:
    cleaned = " ".join(statement.strip().split())
    return NormalizedIntent(
        original_statement=statement,
        normalized_statement=cleaned,
        source_statement_hash=canonical_hash(cleaned),
        word_count=len(cleaned.split()),
    )


def build_elicitation_request(
    normalized: NormalizedIntent, config: IntentCompilerConfig
) -> StructuredCompletionRequest:
    prompt = (
        "You are the Requirements Analyst agent in an evolutionary software "
        "architecture platform.\n"
        "Analyse the problem statement. Identify business capabilities, make "
        "every assumption explicit, and list clarifications you would seek.\n"
        "Respond ONLY with JSON conforming to the elicitation schema.\n\n"
        f"PROBLEM STATEMENT:\n{normalized.normalized_statement}\n"
    )
    return StructuredCompletionRequest(
        model_id=config.model_id,
        task=INTENT_ELICITATION_TASK,
        prompt=prompt,
        output_schema_id=INTENT_ELICITATION_SCHEMA,
        decoding=config.decoding,
    )


def build_extraction_request(
    normalized: NormalizedIntent,
    elicitation: ElicitationOutput,
    config: IntentCompilerConfig,
) -> StructuredCompletionRequest:
    prompt = (
        "You are the Requirements Analyst agent in an evolutionary software "
        "architecture platform.\n"
        "Extract a requirement graph (nodes and edges) from the problem "
        "statement and elicitation context.\n"
        "Node kinds: functional, quality, constraint, compliance, "
        "integration, data, business_rule, assumption.\n"
        "Edge kinds: refines, depends_on, conflicts_with, realizes, "
        "constrains, derives_from.\n"
        "Respond ONLY with JSON conforming to the extraction schema.\n\n"
        f"PROBLEM STATEMENT:\n{normalized.normalized_statement}\n\n"
        "ELICITATION CONTEXT:\n"
        f"{canonical_json(elicitation.model_dump(mode='json'))}\n"
    )
    return StructuredCompletionRequest(
        model_id=config.model_id,
        task=INTENT_EXTRACTION_TASK,
        prompt=prompt,
        output_schema_id=INTENT_EXTRACTION_SCHEMA,
        decoding=config.decoding,
    )


def build_repair_request(
    normalized: NormalizedIntent,
    current: "ExtractionOutput",
    issues: list[str],
    iteration: int,
    config: IntentCompilerConfig,
) -> StructuredCompletionRequest:
    issue_lines = "\n".join(f"- {issue}" for issue in issues)
    prompt = (
        "You are the Software Architect agent repairing a requirement graph.\n"
        "The following issues were detected. Produce a corrected requirement "
        "graph that resolves them without introducing new problems.\n"
        "Respond ONLY with JSON conforming to the repair schema.\n\n"
        f"PROBLEM STATEMENT:\n{normalized.normalized_statement}\n\n"
        "CURRENT GRAPH:\n"
        f"{canonical_json(current.model_dump(mode='json'))}\n\n"
        f"ISSUES:\n{issue_lines}\n\n"
        f"REPAIR ITERATION: {iteration}\n"
    )
    return StructuredCompletionRequest(
        model_id=config.model_id,
        task=INTENT_REPAIR_TASK,
        prompt=prompt,
        output_schema_id=INTENT_REPAIR_SCHEMA,
        decoding=config.decoding,
    )


def derive_system_id(statement: str) -> str:
    return f"sys-{canonical_hash(statement)[:12]}"


# Avoid a circular import at module top while keeping the type hint readable.
from .schemas import ExtractionOutput  # noqa: E402  (late import resolves cycle)
