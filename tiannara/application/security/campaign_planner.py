"""34.4 Attack Campaign Planner -- mandatory/applicable/regression."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash
@dataclass(frozen=True)
class AttackCampaign:
    mandatory: tuple[str,...]; applicable: tuple[str,...]; regression: tuple[str,...]; adversarial: tuple[str,...]; non_applicable: tuple[str,...]; untested: tuple[str,...]
    def campaign_id(self): return canonical_hash((self.mandatory, self.applicable))[:12]

def plan_campaign(surface: list[str], obligations: list[str], taxonomy: list[str], regressions: list[str]) -> AttackCampaign:
    mandatory = tuple(a for a in taxonomy if "critical" in a or "sql" in a)
    applicable = tuple(a for a in taxonomy if any(s in a for s in surface))
    regression = tuple(regressions)
    adversarial = tuple(a for a in taxonomy if a not in mandatory+applicable)[:2]
    non_applicable = tuple(a for a in taxonomy if a not in applicable+mandatory)
    untested = tuple()
    # Never convert non-applicable to success
    return AttackCampaign(mandatory, applicable, regression, adversarial, non_applicable, untested)
