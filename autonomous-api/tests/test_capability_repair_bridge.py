import pytest
from types import SimpleNamespace
from app.engine.capability_repair_bridge import execute_capability_repair
from app.engine.verification_failure_repair import VerificationFailure, VerificationRepairRequest
from app.engine.work_mode import WorkMode

def test_capability_bridge_rejects_wrong_repair_domain():
    request=VerificationRepairRequest(
        (VerificationFailure("v","crawlability","failed",("d",)),),
        SimpleNamespace(repair_mutation_id="r",domain="backend"),
        "r",
    )
    with pytest.raises(ValueError, match="repair-domain-mismatch:seo:backend"):
        execute_capability_repair(
            WorkMode.SEO, request, genome=None, repair_specs={}, observations={},
            contracts_by_domain=None, verifiers={}, evidence_by_property={}
        )

def test_capability_bridge_requires_candidate():
    request=VerificationRepairRequest(
        (VerificationFailure("v","crawlability","failed",("d",)),), None, "r"
    )
    with pytest.raises(ValueError, match="missing-verification-repair-mutation"):
        execute_capability_repair(
            WorkMode.SEO, request, genome=None, repair_specs={}, observations={},
            contracts_by_domain=None, verifiers={}, evidence_by_property={}
        )
