"""37.4 Fitness Governance -- proposal→evidence→counterfactual→gate."""
from dataclasses import dataclass
@dataclass(frozen=True)
class FitnessProposal:
    change: str; evidence: str; approved: bool = False
    def is_approved(self, gate_result: bool) -> bool:
        return gate_result and bool(self.evidence)
