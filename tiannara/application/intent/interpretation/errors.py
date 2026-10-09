"""Fail-closed errors for internal specification interpretation.

Interpretation must never fabricate an output for a statement it cannot
reason about; callers receive these ``LanguageModelError`` subtypes instead,
so the port contract (raise, never invent) holds for the internal provider
exactly as it does for replay.
"""

from __future__ import annotations

from tiannara.domain.models.model_call import LanguageModelError


class InterpretationError(LanguageModelError):
    """Base class for internal interpretation failures."""


class PromptStructureError(InterpretationError):
    """The structured request did not carry the sections this provider parses."""


class UninterpretableSpecificationError(InterpretationError):
    """No safe interpretation exists for the given statement.

    Raised when the statement yields no requirements, no persisted entities,
    or otherwise cannot support generation without inventing meaning.
    """
