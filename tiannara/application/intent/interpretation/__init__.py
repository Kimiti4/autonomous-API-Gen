"""Specification-agnostic interpretation of natural-language problem statements.

This package is ESAP's independent interpretation layer. Given only a
normalized statement (never a fixture, transcript, or golden artifact) it
produces the structured elicitation/extraction outputs the IntentCompiler's
deterministic stages consume:

* :func:`interpret_elicitation` -- capabilities, explicit assumptions,
  clarifications;
* :func:`interpret_extraction`  -- requirement-graph seeds + entity designs;
* :func:`interpret_repair`      -- deterministic fixes for pre-validation
  issues raised by ``graph_builder``.

All rules are phrasing-driven and domain-blind; every derived element
carries a source-text hash in its rationale for traceability. Failures raise
``InterpretationError`` subtypes (fail-closed): interpretation never returns
a silently empty result.
"""

from .elicitation import interpret_elicitation
from .errors import (
    InterpretationError,
    PromptStructureError,
    UninterpretableSpecificationError,
)
from .extraction import interpret_extraction
from .repair import interpret_repair

__all__ = [
    "InterpretationError",
    "PromptStructureError",
    "UninterpretableSpecificationError",
    "interpret_elicitation",
    "interpret_extraction",
    "interpret_repair",
]
