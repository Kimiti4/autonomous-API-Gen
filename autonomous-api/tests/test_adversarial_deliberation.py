from app.engine.adversarial_deliberation import (
    generate_challenges, record_challenge, build_deliberation
)

def test_alternatives_challenge_each_other():
    c=generate_challenges(("A","B"),{"A":("low latency",),"B":("low cost",)})
    assert len(c)==2
    assert {x.challenger for x in c}=={"A","B"}

def test_challenge_requires_evidence():
    c=generate_challenges(("A","B"),{"B":("reliable",)})[0]
    try:
        record_challenge(c,"supported","","observed")
        assert False
    except ValueError:
        pass

def test_inconclusive_challenge_remains_unresolved():
    c=generate_challenges(("A","B"),{"B":("reliable",)})[0]
    r=record_challenge(c,"inconclusive","e1","insufficient evidence")
    d=build_deliberation("D1",("A","B"),(c,),(r,))
    assert d.unresolved==(c.challenge_id,)

def test_supported_challenge_closes():
    c=generate_challenges(("A","B"),{"B":("reliable",)})[0]
    r=record_challenge(c,"supported","e1","stress test passed")
    d=build_deliberation("D1",("A","B"),(c,),(r,))
    assert not d.unresolved
