"""D06 regression: DAST must execute through a scanner, never simulate.

The previous campaign derived "blocked" from a hash suffix. These tests pin
the fail-closed contract: no scanner means no verdict, every attack is
dispatched to the injected client, and outcomes are preserved verbatim in the
ledger.
"""

from __future__ import annotations

import pytest

from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.security.dast_campaign import (
    DASTNotConfigured,
    run_dast,
)


class _Scanner:
    def __init__(self, outcomes: dict[tuple[str, str], bool] | None = None) -> None:
        self.calls: list[tuple[str, str, int]] = []
        self.outcomes = outcomes or {}

    def attack(self, artifact: str, attack: str, seed: int) -> bool:
        self.calls.append((artifact, attack, seed))
        return self.outcomes.get((artifact, attack), attack.endswith("0"))


def test_dast_requires_scanner_client():
    ledger = EvolutionLedger()

    with pytest.raises(DASTNotConfigured):
        run_dast(["art"], ["sqli"], ledger)

    assert ledger.event_count == 0


def test_dast_rejects_empty_inputs():
    scanner = _Scanner()

    with pytest.raises(ValueError):
        run_dast([], ["sqli"], EvolutionLedger(), client=scanner)
    with pytest.raises(ValueError):
        run_dast(["art"], [], EvolutionLedger(), client=scanner)

    assert scanner.calls == []


def test_dast_dispatches_every_attack_to_the_scanner():
    ledger = EvolutionLedger()
    scanner = _Scanner()

    results = run_dast(["a", "b"], ["x", "y", "z"], ledger, seed=7, client=scanner)

    assert len(results) == 6
    assert scanner.calls == [
        (artifact, attack, 7)
        for artifact in ["a", "b"]
        for attack in ["x", "y", "z"]
    ]
    assert ledger.event_count == 6
    assert ledger.verify_event_chain() is True


def test_dast_preserves_real_outcomes_in_results_and_ledger():
    ledger = EvolutionLedger()
    scanner = _Scanner({("art", "blocked"): True, ("art", "allowed"): False})

    results = run_dast(["art"], ["blocked", "allowed"], ledger, client=scanner)

    assert [result.blocked for result in results] == [True, False]
    events = ledger.events()
    assert [event.payload["blocked"] for event in events] == [True, False]
    assert all(event.payload["seed"] == 42 for event in events)


def test_dast_scanner_failure_propagates():
    class _Boom:
        def attack(self, artifact: str, attack: str, seed: int) -> bool:
            raise RuntimeError("scanner crashed")

    ledger = EvolutionLedger()

    with pytest.raises(RuntimeError, match="scanner crashed"):
        run_dast(["art"], ["atk"], ledger, client=_Boom())

    assert ledger.event_count == 0


def test_dast_rejects_non_boolean_scanner_outcome():
    class _Liar:
        def attack(self, artifact: str, attack: str, seed: int) -> bool:
            return "yes"  # type: ignore[return-value]

    with pytest.raises(TypeError):
        run_dast(["art"], ["atk"], EvolutionLedger(), client=_Liar())


def test_dast_event_ids_are_unique_for_duplicate_inputs():
    ledger = EvolutionLedger()

    results = run_dast(["art", "art"], ["atk"], ledger, client=_Scanner())

    refs = [result.ledger_ref for result in results]
    assert len(refs) == 2
    assert refs[0] != refs[1]
    assert ledger.verify_event_chain() is True
