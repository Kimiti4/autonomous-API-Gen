"""
Requirement Extraction.

Provides the interface for extracting structured requirements
from natural language input.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from constitutional_architecture.isr.irr.model import IRR


class RequirementExtractor(ABC):
    """
    Abstract interface for requirement extraction.

    Implementations may use NLP, LLMs, or manual structuring.
    The interface is technology-neutral.
    """

    @abstractmethod
    def extract(self, natural_language_input: str) -> IRR:
        ...

    @abstractmethod
    def refine(self, irr: IRR, feedback: str) -> IRR:
        ...


class ManualRequirementExtractor(RequirementExtractor):
    """
    A manual requirement extractor that returns a pre-built IRR.

    Used for testing and initial development.
    """

    def __init__(self, prebuilt_irr: IRR) -> None:
        self._irr = prebuilt_irr

    def extract(self, natural_language_input: str) -> IRR:
        return self._irr

    def refine(self, irr: IRR, feedback: str) -> IRR:
        return irr
