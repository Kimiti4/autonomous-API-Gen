from app.engine.verification_compiler import adapter_for, build_verification_plan
from app.engine.verification_obligations import VerificationObligation

def obligation():
    return VerificationObligation("x","idempotency","transfer","repeat request","one effect")

def test_plan_requires_evidence_for_each_obligation():
    p=build_verification_plan((obligation(),))
    assert p.fail_closed
    assert p.required_evidence == ("x:execution-result",)

def test_targets_share_semantics():
    assert adapter_for("python").supported_categories == adapter_for("swift").supported_categories
    assert adapter_for("node").supported_categories == adapter_for("kotlin").supported_categories

def test_unknown_target_is_not_silently_accepted():
    try:
        adapter_for("unknown")
        assert False
    except ValueError:
        pass
