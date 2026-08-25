"""35.2 Chaos Injector -- env, target, seed, ledger."""
from dataclasses import dataclass
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
@dataclass(frozen=True)
class Injection: env: str; target: str; failure: str; seed: int; ref: str
def inject(env: str, target: str, failure: str, seed: int, ledger: EvolutionLedger):
    ref = ledger.append_event(EvolutionEvent(event_id=f"chaos-{failure}-{seed}", evolution_id=env, sequence=0, event_type=EventType.CERTIFICATION, subject_id=target, payload={"failure": failure, "seed": seed}), evolution_id=env)
    return Injection(env, target, failure, seed, ref)
