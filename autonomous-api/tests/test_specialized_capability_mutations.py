import pytest
from app.engine.specialized_capability_mutations import (
    architecture_mutation, documentation_mutation, migration_mutation,
    refactor_mutation, test_mutation,
)


@pytest.mark.parametrize("factory,risk,domain", [
    (documentation_mutation, "low", "documentation"),
    (test_mutation, "medium", "testing"),
    (architecture_mutation, "high", "architecture"),
    (migration_mutation, "high", "migration"),
    (refactor_mutation, "high", "refactor"),
])
def test_bucket_two_capability_operators_require_domain_verification(factory, risk, domain):
    spec = factory("m1", ("x",), "reason", ("evidence",), lambda genome: genome)
    assert spec.mutation.domain == domain
    assert spec.risk_class == risk
    assert spec.verification_properties
