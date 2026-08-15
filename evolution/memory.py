"""
Evolutionary memory.

This module stores campaign-level evolutionary evidence:
- generation summaries
- elite candidates
- objective trends
"""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel, Field

from .models import utcnow
from .utils import deterministic_id


class GenerationSummary(BaseModel):
    """Summary of one evolution generation."""

    id: str

    campaign_id: str
    generation_index: int

    proposal_id: str
    genome_id: str

    selected_candidate_id: Optional[str] = None

    status: str = ""

    objectives: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, bool] = Field(default_factory=dict)

    elite_count: int = 0

    created_at: str


class EliteRecord(BaseModel):
    """Record of an elite candidate preserved in evolutionary memory."""

    id: str

    campaign_id: str
    generation_index: int

    proposal_id: str
    candidate_id: str
    genome_id: str

    isr_content_hash: str

    objectives: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, bool] = Field(default_factory=dict)

    created_at: str


class CampaignTrend(BaseModel):
    """Trend information for a campaign."""

    campaign_id: str

    generation_count: int = 0

    objective_trends: dict[str, list[Optional[float]]] = Field(
        default_factory=dict
    )

    selected_candidate_ids: list[Optional[str]] = Field(default_factory=list)

    elite_count: int = 0


class MemoryPolicy(BaseModel):
    """Policy controlling evolutionary memory behavior."""

    max_elites: int = Field(default=50, ge=1, le=1000)
    dedupe_by_content_hash: bool = True


class EvolutionaryMemoryStore(Protocol):
    """Abstract evolutionary memory store."""

    def save_generation_summary(self, summary: GenerationSummary) -> None:
        ...

    def save_elite(self, elite: EliteRecord) -> bool:
        ...

    def list_generation_summaries(
        self,
        campaign_id: str,
    ) -> List[GenerationSummary]:
        ...

    def list_elites(self, campaign_id: str) -> List[EliteRecord]:
        ...

    def get_trend(self, campaign_id: str) -> CampaignTrend:
        ...


class InMemoryEvolutionaryMemory:
    """In-memory evolutionary memory store."""

    def __init__(self, policy: Optional[MemoryPolicy] = None) -> None:
        self.policy = policy or MemoryPolicy()

        self._summaries: Dict[str, List[GenerationSummary]] = {}
        self._elites: Dict[str, List[EliteRecord]] = {}
        self._elite_content_hashes: Dict[str, set[str]] = {}

    def save_generation_summary(self, summary: GenerationSummary) -> None:
        summaries = self._summaries.setdefault(summary.campaign_id, [])
        summaries.append(summary)

    def save_elite(self, elite: EliteRecord) -> bool:
        elites = self._elites.setdefault(elite.campaign_id, [])

        hashes = self._elite_content_hashes.setdefault(elite.campaign_id, set())

        if self.policy.dedupe_by_content_hash:
            if elite.isr_content_hash in hashes:
                return False

        elites.append(elite)

        hashes.add(elite.isr_content_hash)

        while len(elites) > self.policy.max_elites:
            removed = elites.pop(0)
            hashes.discard(removed.isr_content_hash)

        return True

    def list_generation_summaries(
        self,
        campaign_id: str,
    ) -> List[GenerationSummary]:
        summaries = self._summaries.get(campaign_id, [])

        return sorted(
            summaries,
            key=lambda summary: summary.generation_index,
        )

    def list_elites(self, campaign_id: str) -> List[EliteRecord]:
        return list(self._elites.get(campaign_id, []))

    def get_trend(self, campaign_id: str) -> CampaignTrend:
        summaries = self.list_generation_summaries(campaign_id)

        objective_names = sorted(
            {
                objective_name
                for summary in summaries
                for objective_name in summary.objectives.keys()
            }
        )

        objective_trends: Dict[str, List[Optional[float]]] = {}

        for objective_name in objective_names:
            objective_trends[objective_name] = [
                summary.objectives.get(objective_name)
                for summary in summaries
            ]

        selected_candidate_ids = [
            summary.selected_candidate_id
            for summary in summaries
        ]

        elite_count = len(self._elites.get(campaign_id, []))

        return CampaignTrend(
            campaign_id=campaign_id,
            generation_count=len(summaries),
            objective_trends=objective_trends,
            selected_candidate_ids=selected_candidate_ids,
            elite_count=elite_count,
        )
