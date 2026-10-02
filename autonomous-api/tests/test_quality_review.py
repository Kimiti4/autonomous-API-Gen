from app.engine.quality_profiles import profile_for
from app.engine.engineering_deliberation import *
from app.engine.quality_review import review_quality

def test_quality_review_blocks_unconsidered_quality():
    d=EngineeringDeliberation("new web system",(),(
        ArchitectureAlternative("A","simple"),
        ArchitectureAlternative("B","distributed"),
    ),(),(Challenge("C1","A","security risk","security test"),
          Challenge("C2","B","performance risk","load test")))
    r=review_quality(profile_for("fullstack"),d)
    assert not r.approved
    assert r.missing_obligations

def test_quality_review_accepts_explicit_engineering_concerns():
    d=EngineeringDeliberation(
      "secure fullstack application with user flow, api contract and data integrity",
      (EngineeringConstraint("C","security and performance"),),
      (ArchitectureAlternative("A","modular architecture with testing and observability"),
       ArchitectureAlternative("B","distributed architecture with reliability")),
      (Tradeoff("performance","A","latency","load test"),),
      (Challenge("C1","A","security failure","security test"),
       Challenge("C2","B","data failure","integration test")),
    )
    r=review_quality(profile_for("fullstack"),d)
    assert r.approved
