"""Failure feedback — classifies stage failures into ISR/genome evolution domains.

CRITICAL RULE: Never let Campaign B repair generated repositories directly.
If generated code fails → evidence → failure classification → ISR/genome
feedback → evolution → new candidate → recompile → retest.

NOT: generated code fails → AI edits code → tests pass.
"""
from __future__ import annotations

STAGE_TO_FEEDBACK: dict[str, str] = {
    "build": "lowering",
    "test": "genome",
    "deploy": "infrastructure",
    "runtime": "architecture",
    "security": "security",
    "semantic": "lowering",
    "structural": "lowering",
    "verify": "provenance",
}


def classify_failure(stage: str) -> str:
    """Map a trial stage failure to the ISR/genome feedback domain.

    Unknown stages default to "genome" (conservative — triggers broader
    architectural re-evaluation).
    """
    return STAGE_TO_FEEDBACK.get(stage, "genome")


ALL_FEEDBACK_DOMAINS: frozenset[str] = frozenset({
    "lowering", "genome", "infrastructure", "architecture",
    "security", "provenance",
})
