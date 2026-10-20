"""33.15 DAST campaign orchestration -- real scanner required, no hardcoding.

Attack outcomes are produced only by an injected ``DASTClient`` that talks to a
running target. Without a client the campaign fails closed rather than
simulating blocks from hashes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash


class DASTNotConfigured(RuntimeError):
    """Raised when no real DAST scanner client has been configured."""


class DASTClient(Protocol):
    """Scanner adapter. Returns True when the target blocked the attack."""

    def attack(self, artifact: str, attack: str, seed: int) -> bool:
        ...


@dataclass(frozen=True)
class DASTResult:
    attack_id: str
    artifact_hash: str
    blocked: bool
    ledger_ref: str


def run_dast(
    artifacts: list[str],
    attacks: list[str],
    ledger: EvolutionLedger,
    seed: int = 42,
    client: DASTClient | None = None,
) -> tuple[DASTResult, ...]:
    if client is None:
        raise DASTNotConfigured(
            "DAST requires an injected scanner client and a running target; "
            "refusing to simulate attack outcomes."
        )
    if not artifacts:
        raise ValueError("DAST requires at least one artifact")
    if not attacks:
        raise ValueError("DAST requires at least one attack")

    results = []
    index = 0
    for art in artifacts:
        for atk in attacks:
            blocked = client.attack(art, atk, seed)
            if not isinstance(blocked, bool):
                raise TypeError("DAST client must return a bool for each attack")
            index += 1
            digest = canonical_hash(f"{index}:{art}:{atk}:{seed}")
            ev = EvolutionEvent(
                event_id=f"dast-{digest[:16]}",
                evolution_id=art,
                sequence=0,
                event_type=EventType.CERTIFICATION,
                subject_id=art,
                payload={"attack": atk, "blocked": blocked, "seed": seed},
            )
            ref = ledger.append_event(ev, evolution_id=art)
            results.append(DASTResult(atk, art, blocked, ref))
    return tuple(results)
