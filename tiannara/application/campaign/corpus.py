"""R2.10.9 — the generation corpus.

Phase 31's generation categories: the shape of the space the campaign
covers. Corpus entries are INTENTS, never ISRs: they enter through the
constitution's Problem → Requirements → Requirement Graph → ISR pipeline —
never directly to code. The corpus seeds the campaign with problems to
solve, not with representations to compile.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProjectCategory(str, Enum):
    """The generation categories — the shape of the space the campaign
    covers (13 categories)."""

    CRUD_SAAS = "CRUD_SAAS"
    ERP = "ERP"
    BANKING = "BANKING"
    HEALTHCARE = "HEALTHCARE"
    LOGISTICS = "LOGISTICS"
    AI_PLATFORM = "AI_PLATFORM"
    GAMING = "GAMING"
    IOT = "IOT"
    ROBOTICS = "ROBOTICS"
    DISTRIBUTED = "DISTRIBUTED"
    EMBEDDED = "EMBEDDED"
    API = "API"
    STREAMING = "STREAMING"


@dataclass(frozen=True)
class CorpusIntent:
    """A generation corpus entry. An INTENT, never an ISR.

    ``acceptance_semantics`` states what must be true of the generated
    system; ``semantic_shape_hints`` is optional semantic guidance — never
    technology.
    """

    intent_id: str
    category: ProjectCategory
    problem_statement: str  # the natural-language problem
    complexity_tier: int  # 1 simple, 2 moderate, 3 complex
    acceptance_semantics: tuple[str, ...]  # what must be true of the result
    semantic_shape_hints: tuple[str, ...] = ()


@dataclass(frozen=True)
class GenerationCorpus:
    corpus_id: str
    intents: tuple[CorpusIntent, ...]

    def categories_covered(self) -> frozenset[ProjectCategory]:
        return frozenset(intent.category for intent in self.intents)