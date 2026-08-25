"""V1-09 SnapshotAggregator -- data.facets is aggregated projections, not log summary."""
import pytest
from unittest.mock import AsyncMock
from app.observation.snapshot_aggregator import SnapshotAggregator

@pytest.mark.asyncio
async def test_snapshot_data_is_aggregated_facets_not_log_summary():
    isr_proj = AsyncMock()
    isr_proj.project.return_value.model_dump.return_value = {"domains": [{"name": "test"}]}
    fitness_proj = AsyncMock()
    fitness_proj.project.return_value.model_dump.return_value = {"generation": 1}
    gov_proj = AsyncMock()
    gov_proj.project_generation.return_value.model_dump.return_value = {"decisions": []}
    agg = SnapshotAggregator(isr_projector=isr_proj, fitness_projector=fitness_proj, governance_projector=gov_proj, lineage_available=True)
    data = await agg.aggregate(current_generation=1)
    assert "facets" in data
    assert data["facets"]["isr"] is not None
    assert data["facets"]["fitness"] is not None
    assert data["facets"]["governance"] is not None
    assert data["generation"] == 1

@pytest.mark.asyncio
async def test_snapshot_data_facets_non_empty_for_seeded_generation():
    isr_proj = AsyncMock()
    isr_proj.project.return_value.model_dump.return_value = {"services": []}
    fitness_proj = AsyncMock()
    fitness_proj.project.return_value.model_dump.return_value = {"candidates": []}
    gov_proj = AsyncMock()
    gov_proj.project_generation.return_value.model_dump.return_value = {"decisions": []}
    agg = SnapshotAggregator(isr_projector=isr_proj, fitness_projector=fitness_proj, governance_projector=gov_proj, lineage_available=False)
    data = await agg.aggregate(current_generation=0)
    assert data["facets"]["isr"] is not None
