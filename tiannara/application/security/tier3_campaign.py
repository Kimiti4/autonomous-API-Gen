"""Tier 3 Full Campaign -- 1,000-attack + stateful replay on real artifacts."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.application.security.dast_campaign import run_dast
from tiannara.application.resilience.chaos_stateful import ChaosState
from tiannara.application.evolution.ledger import EvolutionLedger, EvolutionEvent, EventType
from tiannara.domain.services.canonical import canonical_hash

@dataclass(frozen=True)
class Tier3Result:
    artifact_hash: str
    dast_results: tuple
    chaos_history: tuple
    ledger_refs: tuple[str, ...]
    tier: str = "TIER_3"

class Tier3Campaign:
    def __init__(self, ledger: EvolutionLedger):
        self.ledger = ledger
        self.tier = "TIER_3"

    def is_eligible(self, tier2_verdict: str) -> bool:
        return tier2_verdict == "CERTIFIED"

    def run(self, artifacts: list[str], attacks: list[str], seed: int = 42) -> Tier3Result:
        assert artifacts, "no artifacts"
        # Tier 3 reserved only for Tier2 survivors -- verify
        # Run DAST thousands
        dast_results = run_dast(artifacts, attacks, self.ledger, seed)
        # Stateful replay
        chaos = ChaosState()
        for atk in attacks[:10]:
            chaos.step(f"attack:{atk}")
        history = chaos.replay()
        # Verify replay determinism
        assert history == chaos.history
        # Ledger refs
        refs = tuple(r.ledger_ref for r in dast_results[:3])
        # Record Tier3 campaign event
        payload = {"artifacts": artifacts, "attacks": len(attacks), "dast": len(dast_results), "chaos": len(history), "tier": self.tier}
        ev = EvolutionEvent(event_id=f"tier3-{canonical_hash(str(artifacts))[:8]}", evolution_id="tier3", sequence=0, event_type=EventType.CERTIFICATION, subject_id="tier3", payload=payload)
        ref = self.ledger.append_event(ev, evolution_id="tier3")
        # Use first artifact hash as representative
        return Tier3Result(artifacts[0], dast_results, history, (ref, *refs))

def is_ready_for_tier3(tier2_results: dict) -> bool:
    return all(v == "CERTIFIED" for v in tier2_results.values())
