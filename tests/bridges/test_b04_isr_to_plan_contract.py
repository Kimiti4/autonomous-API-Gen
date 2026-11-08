from certification.bridges.transformation_contracts import (
    B04_ISR_TO_PLAN,
    assert_trusted_bridge_allowed,
    get_bridge_contract,
)


def test_b04_registered_lossy_explicit():
    c = get_bridge_contract("B-04")
    assert c is B04_ISR_TO_PLAN
    assert c.lossiness.value == "LOSSY_EXPLICIT"
    assert_trusted_bridge_allowed("B-04")
