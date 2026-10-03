from app.engine.verification_obligations import VerificationObligation
from app.engine.verification_artifacts import VerificationExecution
from app.engine.multi_target_equivalence import derive_equivalence_claim, verify_target_equivalence, target_result_from_execution

def claim():
    return derive_equivalence_claim(
        VerificationObligation("transfer","idempotency","transfer","repeat","one effect"),
        ("single-authoritative-effect","authorization-preserved"),
    )

def result(target, behavior="one-effect", invariants=("single-authoritative-effect","authorization-preserved")):
    e=VerificationExecution(f"{target}:transfer","passed",("observed",),"runner")
    return target_result_from_execution(target,"transfer",e,behavior,invariants)

def test_two_targets_can_pass_equivalence():
    v=verify_target_equivalence(claim(),(result("python"),result("node")))
    assert v.verdict=="PASS"

def test_missing_invariant_fails_equivalence():
    v=verify_target_equivalence(claim(),(result("python"),result("swift",invariants=("single-authoritative-effect",))))
    assert v.verdict=="FAIL"

def test_behavior_difference_is_not_silently_passed():
    v=verify_target_equivalence(claim(),(result("python"),result("kotlin","two-effects")))
    assert v.verdict=="INCONCLUSIVE"

def test_single_target_is_inconclusive():
    v=verify_target_equivalence(claim(),(result("python"),))
    assert v.verdict=="INCONCLUSIVE"
