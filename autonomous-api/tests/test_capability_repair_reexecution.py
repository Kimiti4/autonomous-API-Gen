import pytest
from types import SimpleNamespace
from app.engine.capability_repair_reexecution import reexecute_capability_repair
from app.engine.verification_failure_repair import VerificationFailure, VerificationRepairRequest
from app.engine.work_mode import WorkMode

def req():
    return VerificationRepairRequest(
        (VerificationFailure("v","crawlability","failed",("d",)),),
        SimpleNamespace(domain="seo", repair_mutation_id="r"), "repair"
    )

def test_capability_reexecution_requires_repair_execution():
    with pytest.raises(ValueError, match="missing-capability-repair-execution"):
        reexecute_capability_repair(
            WorkMode.SEO, req(), None, result=None, dependency_graph={},
            dependent_specs=(), verifiers={}, observations={}, evidence_by_property={},
            successor_architecture_id="s"
        )

def test_capability_route_is_checked_before_reexecution():
    bad=VerificationRepairRequest(
        (VerificationFailure("v","unrelated","failed",("d",)),),
        SimpleNamespace(domain="seo", repair_mutation_id="r"), "repair"
    )
    with pytest.raises(ValueError, match="no-capability-failure-to-route:seo"):
        reexecute_capability_repair(
            WorkMode.SEO, bad, SimpleNamespace(), result=None, dependency_graph={},
            dependent_specs=(), verifiers={}, observations={}, evidence_by_property={},
            successor_architecture_id="s"
        )
