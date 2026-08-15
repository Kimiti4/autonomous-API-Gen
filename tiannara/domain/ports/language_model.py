"""LanguageModelProvider port.

Dependency-inverted boundary for structured language-model completion.
Concrete providers (live vendors, recorded replay, recording decorators)
implement or wrap this protocol. Replay and recording are first-class so
every downstream capability can run hermetically and be certified
reproducibly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from ..models.model_call import ModelCallRecord, StructuredCompletionRequest

OutputT = TypeVar("OutputT", bound=BaseModel)


@dataclass(frozen=True)
class StructuredCompletionResult(Generic[OutputT]):
    """Validated structured output plus its provenance record."""

    output: OutputT
    record: ModelCallRecord


@runtime_checkable
class LanguageModelProvider(Protocol):
    def complete_structured(
        self,
        request: StructuredCompletionRequest,
        output_type: type[OutputT],
    ) -> StructuredCompletionResult[OutputT]:
        """Return a schema-validated output and its provenance record.

        Implementations must raise ``LanguageModelError`` subtypes on failure;
        they must never fabricate an output for an unavailable model.
        """
        ...
