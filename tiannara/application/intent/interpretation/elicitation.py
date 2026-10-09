"""Stage 2 interpretation: capabilities, assumptions, clarifications.

Deterministic, specification-agnostic analysis of the normalized statement.
There is no task-specific knowledge here: rules key on generic requirement
phrasing (capability verbs, explicit scope statements, vagueness markers).
"""

from __future__ import annotations

import re

from ..schemas import AssumptionSeed, ElicitationOutput, NormalizedIntent
from .errors import UninterpretableSpecificationError
from .text import iter_sentences, source_hash

_CAPABILITY_VERBS = (
    "create", "record", "track", "manage", "organize", "organise", "list",
    "fetch", "store", "submit", "approve", "reject", "review", "update",
    "change", "mark", "delete", "remove", "share", "group", "report",
    "schedule", "book", "cancel", "notify", "search", "filter", "show",
    "display", "reach", "access", "log", "register", "maintain",
)

_SCOPE_PATTERNS = (
    r"\bone person\b",
    r"\bsmall team\b",
    r"\bper installation\b",
    r"\bsingle maintainer\b",
    r"\bstandalone\b",
    r"\bsmall (?:team|group|office)\b",
    r"\bno cross[- ]",
    r"\bone (?:site|office|workspace)\b",
)

_VAGUENESS_PATTERNS = (
    r"\bTBD\b",
    r"\bto be determined\b",
    r"\betc\.?",
    r"\band so on\b",
    r"\bsomehow\b",
    r"\bas (?:needed|required|appropriate)\b",
    r"\bappropriate(?:ly)?\b",
    r"\bwhatever\b",
    r"\bunspecified\b",
    r"\broughly\b",
)

_CAPABILITY_VERB_SET = frozenset(_CAPABILITY_VERBS)
_MAX_CAPABILITIES = 12


def _contains_capability_verb(sentence: str) -> bool:
    for token in re.findall(r"[a-z]+", sentence.lower()):
        if token in _CAPABILITY_VERB_SET:
            return True
    return False


def interpret_elicitation(normalized: NormalizedIntent) -> ElicitationOutput:
    """Derive capabilities, explicit assumptions, and clarifications.

    Raises ``UninterpretableSpecificationError`` when the statement carries no
    analyzable content at all -- interpretation must fail closed rather than
    emit an empty-but-successful result.
    """
    statement = normalized.normalized_statement
    if normalized.word_count < 6 or len(statement.strip()) < 20:
        raise UninterpretableSpecificationError(
            "statement is too short to interpret safely: "
            f"{normalized.word_count} words"
        )

    sentences = iter_sentences(statement)
    if not sentences:
        raise UninterpretableSpecificationError("no sentences found in statement")

    capabilities: list[str] = []
    seen_caps: set[str] = set()
    assumptions: list[AssumptionSeed] = []
    seen_assumptions: set[str] = set()
    clarifications: list[str] = []

    for sentence in sentences:
        lowered = sentence.lower()
        if _contains_capability_verb(sentence) and len(sentence) <= 160:
            key = sentence.lower()
            if key not in seen_caps:
                seen_caps.add(key)
                capabilities.append(sentence)
        for pattern in _SCOPE_PATTERNS:
            if re.search(pattern, lowered):
                key = sentence.lower()
                if key not in seen_assumptions:
                    seen_assumptions.add(key)
                    assumptions.append(
                        AssumptionSeed(
                            statement=sentence,
                            rationale=(
                                "explicit scope described in the source text "
                                f"({source_hash(sentence)})"
                            ),
                        )
                    )
                break
        for pattern in _VAGUENESS_PATTERNS:
            if re.search(pattern, lowered):
                clarifications.append(
                    f"vague phrasing in source text {source_hash(sentence)}: "
                    f"{sentence!r} needs a concrete definition"
                )
                break

    if not capabilities and not assumptions:
        raise UninterpretableSpecificationError(
            "statement yielded no recognizable capabilities or scope statements"
        )

    return ElicitationOutput(
        inferred_capabilities=capabilities[:_MAX_CAPABILITIES],
        assumptions=assumptions,
        clarifications=clarifications,
    )
