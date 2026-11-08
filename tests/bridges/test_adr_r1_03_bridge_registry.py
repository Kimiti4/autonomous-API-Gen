"""ADR-R1-03 minimum bridge contract registry (R1-W07)."""

from __future__ import annotations

import pytest

from certification.bridges.lossiness_policy import (
    trusted_compile_allowed,
    trusted_promotion_allowed,
)
from certification.bridges.transformation_contracts import (
    ADR_R1_03_MINIMUM_BRIDGE_IDS,
    LossinessClass,
    assert_trusted_bridge_allowed,
    get_bridge_contract,
)


@pytest.mark.parametrize("bridge_id", ADR_R1_03_MINIMUM_BRIDGE_IDS)
def test_minimum_set_registered(bridge_id: str):
    contract = get_bridge_contract(bridge_id)
    assert contract.bridge_id == bridge_id
    assert contract.verification_method
    assert contract.failure_behavior == "FAIL_CLOSED"


def test_only_b03_and_b04_trusted_on_governed_compile_path():
    trusted = [
        bid
        for bid in ADR_R1_03_MINIMUM_BRIDGE_IDS
        if get_bridge_contract(bid).trusted_compile_allowed
    ]
    assert set(trusted) == {"B-03", "B-04"}


def test_b07_b09_unsupported_fail_closed():
    for bid in ("B-07", "B-09"):
        c = get_bridge_contract(bid)
        assert c.lossiness is LossinessClass.UNSUPPORTED_FAIL_CLOSED
        assert not c.trusted_compile_allowed
        assert not trusted_promotion_allowed(c)
        with pytest.raises(ValueError, match="unsupported-fail-closed|not-trusted"):
            assert_trusted_bridge_allowed(bid)


def test_b04_trusted_with_lossiness_policy():
    c = get_bridge_contract("B-04")
    assert trusted_compile_allowed(c)
    assert_trusted_bridge_allowed("B-04")
