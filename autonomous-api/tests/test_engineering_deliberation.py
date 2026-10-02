from app.engine.engineering_deliberation import (
    ArchitectureAlternative, Challenge, EngineeringConstraint,
    EngineeringDeliberation, Tradeoff, validate_deliberation,
)


def test_deliberation_requires_alternatives_challenges_and_evidence():
    d = EngineeringDeliberation(
        "telemetry platform",
        (EngineeringConstraint("C1", "10k events/sec"),),
        (
            ArchitectureAlternative("A", "stream-first", benefits=("throughput",)),
            ArchitectureAlternative("B", "database-first", costs=("write load",)),
        ),
        (Tradeoff("throughput", "A", "higher ingestion complexity", ("load-test",)),),
        (Challenge("CH1", "A", "backpressure risk", "sustained-load-test"),),
        selected_alternative="A",
        selection_rationale="meets the hard throughput constraint under measured load",
    )
    assert validate_deliberation(d) == ()


def test_deliberation_rejects_single_unchallenged_design():
    d = EngineeringDeliberation(
        "x", (), (ArchitectureAlternative("A", "only design"),), (), ()
    )
    findings = validate_deliberation(d)
    assert any("two alternatives" in x for x in findings)
    assert any("challenge" in x for x in findings)
