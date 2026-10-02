from app.engine.engineering_deliberation import (
    ArchitectureAlternative, Challenge, EngineeringDeliberation, Tradeoff,
)
from app.engineering_review import review_deliberation


def test_review_requires_each_candidate_to_be_challenged():
    d = EngineeringDeliberation(
        "x", (),
        (ArchitectureAlternative("A", "a"), ArchitectureAlternative("B", "b")),
        (Tradeoff("cost", "A", "higher", ("benchmark",)),),
        (Challenge("C", "A", "risk", "test"),),
        selected_alternative="A", selection_rationale="evidence",
    )
    review = review_deliberation(d)
    assert not review.approved_for_architecture
    assert any("unchallenged" in x for x in review.findings)


def test_review_blocks_unresolved_questions():
    d = EngineeringDeliberation(
        "x", (),
        (ArchitectureAlternative("A", "a"), ArchitectureAlternative("B", "b")),
        (Tradeoff("cost", "A", "higher", ("benchmark",)),),
        (Challenge("C1", "A", "risk", "test"), Challenge("C2", "B", "risk", "test")),
        unresolved=("database consistency unknown",),
        selected_alternative="A", selection_rationale="evidence",
    )
    assert not review_deliberation(d).approved_for_architecture
