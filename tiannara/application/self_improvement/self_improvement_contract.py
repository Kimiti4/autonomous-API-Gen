"""37.0 Self-Audit Contract -- compiler/fitness/genome immutable boundaries."""
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash
@dataclass(frozen=True)
class SelfImprovementContract:
    contract_id: str; boundaries: tuple[str,...]; content_hash: str
    def allows(self, target: str) -> bool: return target in self.boundaries
def build_self_improvement_contract():
    boundaries=("compiler","fitness","genome","mutation","architecture_knowledge","plugins")
    tmp=SelfImprovementContract("self-improvement-001", boundaries, "")
    h=canonical_hash({"contract_id": tmp.contract_id, "boundaries": list(boundaries)})
    return SelfImprovementContract(tmp.contract_id, boundaries, h)
SELF_IMPROVEMENT_CONTRACT=build_self_improvement_contract()
