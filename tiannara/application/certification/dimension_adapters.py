"""Dimension adapters -- explicit, immutable, no guessing."""
from __future__ import annotations
from tiannara.application.certification.production_readiness import DimensionVerdict

def adapt_compiler(native: str) -> DimensionVerdict:
    mapping = {"CERTIFIED": DimensionVerdict.CERTIFIED, "BOUNDED_SUCCESS": DimensionVerdict.BOUNDED, "NOT_CERTIFIED": DimensionVerdict.NOT_CERTIFIED, "BOUNDED": DimensionVerdict.BOUNDED}
    if native not in mapping:
        raise ValueError(f"unknown compiler verdict {native}")
    return mapping[native]

def adapt_engineering(native: str) -> DimensionVerdict:
    mapping = {"CERTIFIED": DimensionVerdict.CERTIFIED, "QUALIFIED_PARTIAL": DimensionVerdict.NOT_CERTIFIED, "NOT_CERTIFIED": DimensionVerdict.NOT_CERTIFIED, "BOUNDED": DimensionVerdict.BOUNDED}
    if native not in mapping:
        raise ValueError(f"unknown engineering verdict {native}")
    return mapping[native]

def adapt_security(native: str) -> DimensionVerdict:
    mapping = {"CERTIFIED": DimensionVerdict.CERTIFIED, "BOUNDED": DimensionVerdict.BOUNDED, "NOT_CERTIFIED": DimensionVerdict.NOT_CERTIFIED, "NOT_TESTED": DimensionVerdict.NOT_TESTED}
    if native not in mapping:
        raise ValueError(f"unknown security verdict {native}")
    return mapping[native]

def adapt_resilience(native: str) -> DimensionVerdict:
    mapping = {"RECOVERED": DimensionVerdict.CERTIFIED, "BOUNDED": DimensionVerdict.BOUNDED, "FAILED": DimensionVerdict.NOT_CERTIFIED, "NOT_STARTED": DimensionVerdict.NOT_TESTED}
    if native not in mapping:
        raise ValueError(f"unknown resilience verdict {native}")
