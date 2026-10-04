import pytest

from app.engine.repair_engine_bridge import execute_verification_repair


def test_missing_candidate_fails_closed():
    class Request:
        candidate = None
    with pytest.raises(ValueError, match="missing-verification-repair-mutation"):
        execute_verification_repair(
            Request(), genome=None, repair_specs={}, observations={},
            contracts_by_domain=None, verifiers={}, evidence_by_property={},
        )
