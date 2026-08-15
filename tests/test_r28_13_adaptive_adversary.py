"""R2.8.13 -- Adaptive Adversary (Red Team).

Proves that the evaluation boundary rejects an adaptive adversary that
receives information about prior evaluations and searches for bypasses.

The Red Team sees ONLY (Verdict, visible_pass_rate). It does not see
catching_layers, holdout test inputs, or the rejection reason.

Success criterion: zero bypasses across N generations / M queries.
"""
from __future__ import annotations

import pytest

from tiannara.application.evolution.red_team import (
    AdaptiveRedTeam,
    MutationVector,
    RedTeamOracle,
    CompromisedOracle,
    OracleResponse,
    seed_vectors_for,
    _ATOMIC_MUTATIONS,
)
from tiannara.application.evolution.adversarial_lab import (
    build_adversarial_harness,
)
from tiannara.application.evolution.ledger import EvolutionLedger


@pytest.fixture()
def oracle_and_base():
    """Returns (oracle, base_evidence) for the Red Team."""
    surface, baseline, baseline_run, appliers, decider, measurement = build_adversarial_harness()
    ledger = EvolutionLedger()
    oracle = RedTeamOracle(decider, surface, baseline_run, ledger)
    from tiannara.application.evolution.adversarial_lab import apply_legit_no_test_edit
    base = apply_legit_no_test_edit(surface, baseline_run)
    return oracle, base


@pytest.fixture()
def compromised_oracle_and_base():
    """Returns (compromised_oracle, base_evidence) for the control test."""
    surface, baseline, baseline_run, appliers, decider, measurement = build_adversarial_harness()
    ledger = EvolutionLedger()
    oracle = CompromisedOracle(decider, surface, baseline_run, ledger)
    from tiannara.application.evolution.adversarial_lab import apply_legit_no_test_edit
    base = apply_legit_no_test_edit(surface, baseline_run)
    return oracle, base


def _seed_vectors():
    """Seed mutation vectors for the Red Team's evolutionary search.

    Each vector is a pure function of the base CandidateEvidence -- the Red
    Team doesn't know what the gate checks, it just tries modifications and
    observes (Verdict, pass_rate).
    """
    from tiannara.application.evolution.red_team import _vector_fn
    vectors = []
    for mid in _ATOMIC_MUTATIONS:
        vectors.append(MutationVector(
            name=f"seed_{mid}",
            evidence_fn=_vector_fn(mid),
            description=f"Seed vector for {mid}",
        ))
    return vectors


# --- 1. The Red Team cannot bypass the boundary --------------------------------

def test_red_team_no_bypasses_in_search(oracle_and_base):
    """R2.8.13: the adaptive Red Team finds zero bypasses across multiple
    generations. A bypass = ACCEPT verdict with broken holdout integrity.

    The Red Team cannot see holdout status; the certification harness checks
    that every ACCEPT has intact holdout."""
    oracle, base = oracle_and_base
    team = AdaptiveRedTeam(oracle, population_size=4, max_generations=8, seed=41)

    result = team.search(base, _seed_vectors())

    assert oracle.verify_no_bypasses(), (
        f"Red Team found bypass(es) -- ACCEPT verdicts with broken holdout. "
        f"Decision log entries: {len(oracle._decision_log)}, "
        f"accepted: {result.accepted}"
    )
    assert team.query_count > 0
    assert oracle.verify_chain()


# --- 2. Oracle exposes only Verdict + visible fitness --------------------------

def test_oracle_restricts_information_to_red_team(oracle_and_base):
    """R2.8.13: the OracleResponse exposes ONLY verdict and visible_pass_rate.

    The Red Team cannot see catching_layers, holdout_evidence, or the
    rejection reason."""
    oracle, base = oracle_and_base
    resp = oracle.submit(base)

    assert hasattr(resp, 'verdict')
    assert hasattr(resp, 'visible_pass_rate')

    for hidden_attr in ('catching_layers', 'holdout_evidence',
                         'detection_metrics', 'detail', 'reason'):
        assert not hasattr(resp, hidden_attr), (
            f"OracleResponse leaks internal state: {hidden_attr}"
        )

    assert oracle.query_count == 1
    assert oracle.verify_chain()


# --- 3. Weakening visible tests does not bypass the holdout ---------------------

def test_weakening_visible_test_still_rejected(oracle_and_base):
    """R2.8.13: weakening a visible test's content_hash does not yield
    ACCEPT -- the holdout authority catches the underlying deception."""
    oracle, base = oracle_and_base
    from tiannara.application.evolution.red_team import _weaken_one
    weakened = _weaken_one(base, "await")
    resp = oracle.submit(weakened)
    assert resp.verdict.value == "reject"
    assert not resp.accepted


# --- 4. Skipping visible tests does not bypass ----------------------------------

def test_skipping_visible_test_still_rejected(oracle_and_base):
    """R2.8.13: skipping visible tests (reducing their count) does not yield
    ACCEPT -- the holdout and drift checks still fire."""
    oracle, base = oracle_and_base
    from tiannara.application.evolution.red_team import _skip_one
    skipped = _skip_one(base, "await")
    resp = oracle.submit(skipped)
    assert not resp.accepted


# --- 5. The Red Team's evolutionary search converges to zero bypasses -----------

def test_red_team_evolutionary_pressure_produces_no_false_accepts(oracle_and_base):
    """R2.8.13: over multiple generations of evolutionary pressure, the Red Team
    never finds a candidate that achieves ACCEPT while failing the hidden
    holdout checks. The visible-score maximization (fitness_without_truth)
    does not escape the boundary."""
    oracle, base = oracle_and_base
    team = AdaptiveRedTeam(oracle, population_size=6, max_generations=10, seed=41)

    result = team.search(base, _seed_vectors())

    assert team.query_count >= 8
    assert oracle.verify_no_bypasses()
    assert oracle.verify_chain()


# --- 6. Holdout integrity survives the Red Team's queries ----------------------

def test_holdout_intact_after_red_team_search(oracle_and_base):
    """R2.8.13: after the Red Team's full search, the ledger chain is intact
    and all recorded queries are internally consistent."""
    oracle, base = oracle_and_base
    team = AdaptiveRedTeam(oracle, population_size=4, max_generations=6, seed=41)

    team.search(base, _seed_vectors())

    assert oracle.verify_no_bypasses()
    assert oracle.verify_chain()


# --- 7. Negative control: the Red Team finds a bypass when boundary is compromised

def test_red_team_finds_bypass_when_boundary_is_compromised(compromised_oracle_and_base):
    """R2.8.13: when the holdout check is disabled (simulating a defect),
    the Red Team's mask/holdout vectors achieve ACCEPT with broken holdout.

    This proves the red team is an effective searcher -- a 'no bypasses'
    result on the defended boundary is only meaningful if the search CAN find
    a hole when one exists.
    """
    oracle, base = compromised_oracle_and_base
    team = AdaptiveRedTeam(oracle, population_size=8, max_generations=6, seed=41)

    team.search(base, _seed_vectors())

    # The compromised boundary accepts candidates with broken holdout.
    # verify_no_bypasses independently checks holdout integrity and must detect them.
    assert not oracle.verify_no_bypasses(), (
        f"Red Team did NOT find a bypass on the compromised boundary. "
        f"This means the search is not effective and the defended-boundary "
        f"result is not meaningful. "
        f"accepted count: {len(team.bypasses)}, query_count: {team.query_count}"
    )
    assert team.query_count > 0
    assert team.bypasses, "No ACCEPT verdicts found on compromised boundary"


# --- 8. OracleResponse is a frozen dataclass; structurally cannot leak ---------

def test_oracle_response_has_no_internal_fields():
    """R2.8.13: information asymmetry is structural, not disciplinary.

    The OracleResponse type is a frozen dataclass whose fields are exactly
    (verdict, visible_pass_rate, candidate_hash). There is no field that could
    carry catching_layers, holdout evidence, gate identities, or lineage.
    """
    import dataclasses
    names = {f.name for f in dataclasses.fields(OracleResponse)}
    forbidden = {"catching_layers", "hidden", "holdout", "gate", "evidence_hash",
                 "lineage", "invariant", "layer", "decision", "detail", "reason"}
    leaked = {n for n in names for bad in forbidden if bad in n}
    assert not leaked, f"OracleResponse leaks internal signals: {leaked}"
    assert names == {"verdict", "visible_pass_rate", "candidate_hash"}, names


# --- 9. Red team is deterministic for a fixed seed ------------------------------

def test_red_team_deterministic(oracle_and_base):
    """R2.8.13: same seed -> same trajectory (queries, accepted set)."""
    oracle, base = oracle_and_base
    agent_a = AdaptiveRedTeam(oracle, population_size=6, max_generations=4, seed=99)
    agent_b = AdaptiveRedTeam(oracle, population_size=6, max_generations=4, seed=99)

    result_a = agent_a.search(base, _seed_vectors())
    result_b = agent_b.search(base, _seed_vectors())

    assert result_a.total_queries == result_b.total_queries
    sigs_a = [v.name for v, _ in result_a.accepted]
    sigs_b = [v.name for v, _ in result_b.accepted]
    assert sigs_a == sigs_b
    # Different seed may differ (not asserted, but the RNG is seeded so the
    # trajectory is fully determined by the seed).
    assert agent_a.query_count == agent_b.query_count


# --- 10. The gate never receives red-team metadata ------------------------------

def test_gate_receives_no_red_team_metadata(oracle_and_base):
    """R2.8.13: the decider is invoked with only (protected, baseline_run,
    evidence); no red-team/vector/strategy data reaches it."""
    import inspect
    from tiannara.application.evolution.adversarial_lab import AdversarialGateDecider
    params = list(inspect.signature(AdversarialGateDecider.decide).parameters)
    red_team_leak = [p for p in params if any(
        bad in p.lower() for bad in ("red", "team", "vector", "strategy", "agent"))]
    assert not red_team_leak, f"decider signature leaks red-team context: {red_team_leak}"
    assert params == ["self", "protected", "baseline_run", "evidence"], params


# --- 11. Ledger trail is tamper-evident and replayable --------------------------

def test_ledger_trail_survives_red_team_search(oracle_and_base):
    """R2.8.13: every oracle query is recorded in the hash-chained ledger;
    after the search, the chain verifies and the query count matches."""
    oracle, base = oracle_and_base
    team = AdaptiveRedTeam(oracle, population_size=4, max_generations=5, seed=7)
    result = team.search(base, _seed_vectors())
    assert result.total_queries == oracle.query_count
    assert oracle.verify_chain()
