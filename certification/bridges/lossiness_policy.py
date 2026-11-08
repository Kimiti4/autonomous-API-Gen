"""ADR-R1-03 lossiness taxonomy enforcement for trusted promotion paths."""

from __future__ import annotations

from certification.bridges.transformation_contracts import LossinessClass, TransformationContract


def trusted_promotion_allowed(contract: TransformationContract) -> bool:
    if contract.lossiness is LossinessClass.UNKNOWN:
        return False
    if contract.lossiness is LossinessClass.UNSUPPORTED_FAIL_CLOSED:
        return False
    return contract.trusted_compile_allowed


def trusted_compile_allowed(contract: TransformationContract) -> bool:
    if contract.lossiness in (
        LossinessClass.UNKNOWN,
        LossinessClass.UNSUPPORTED_FAIL_CLOSED,
    ):
        return False
    return contract.trusted_compile_allowed
