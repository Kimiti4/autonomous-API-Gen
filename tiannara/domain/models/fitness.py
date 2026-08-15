from pydantic import BaseModel, Field


class FitnessVector(BaseModel):
    """Multi-objective fitness. Never collapse to a single aggregate score."""

    metrics: dict[str, float] = Field(default_factory=dict)

    def dominates(self, other: "FitnessVector") -> bool:
        keys = set(self.metrics) & set(other.metrics)
        if not keys:
            return False
        at_least_as_good = all(self.metrics[k] >= other.metrics[k] for k in keys)
        strictly_better = any(self.metrics[k] > other.metrics[k] for k in keys)
        return at_least_as_good and strictly_better
