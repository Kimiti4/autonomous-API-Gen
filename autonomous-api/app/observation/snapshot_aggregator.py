"""V1-09 SnapshotAggregator -- real facets, never log summary."""
class SnapshotAggregator:
    def __init__(self, *, isr_projector, fitness_projector, governance_projector, lineage_available: bool):
        self._isr = isr_projector; self._fitness = fitness_projector; self._governance = governance_projector; self._lineage_available = lineage_available
    async def aggregate(self, *, current_generation: int) -> dict:
        facets = {}
        try: facets["isr"] = (await self._isr.project()).model_dump(mode="json")
        except Exception: facets["isr"] = None
        try: facets["fitness"] = (await self._fitness.project(current_generation)).model_dump(mode="json")
        except Exception: facets["fitness"] = None
        try: facets["governance"] = (await self._governance.project_generation(current_generation)).model_dump(mode="json")
        except Exception: facets["governance"] = None
        return {"facets": facets, "generation": current_generation}
