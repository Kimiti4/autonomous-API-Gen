import pytest
from app.engine.mode_capability_mutations import generate_mutation, maintain_mutation, improve_mutation, seo_mutation, cross_stack_mutation


@pytest.mark.parametrize("factory,domain,risk", [
    (generate_mutation, "generate", "high"),
    (maintain_mutation, "maintain", "high"),
    (improve_mutation, "improve", "high"),
    (seo_mutation, "seo", "medium"),
    (cross_stack_mutation, "crossstack", "critical"),
])
def test_mode_operators_are_evidence_gated(factory, domain, risk):
    spec = factory("m", ("x",), "why", ("e",), lambda g: g)
    assert spec.mutation.domain == domain
    assert spec.risk_class == risk
    assert spec.verification_properties
