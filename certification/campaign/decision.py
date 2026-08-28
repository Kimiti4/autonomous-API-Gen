"""B3 decision boundary — encoded campaign-to-campaign policy.

CERTIFIED + honest retries   -> proceed to larger scale.
QUALIFIED_PARTIAL            -> analyze infra transience + retry honesty; do NOT scale.
Product/semantic/compiler    -> STOP scaling; fix the actual defect first.
Retry dishonesty             -> NOT_CERTIFIED regardless of execution counts.
Evidence-integrity failure   -> NOT_CERTIFIED regardless of execution counts.
"""
from __future__ import annotations
from typing import Any


def b3_decision(
    verdict: str,
    amp: Any,
    max_retry_rate: float = 0.2,
) -> str:
    """Map a campaign outcome to the next-action decision."""
    if amp is not None:
        if getattr(amp, "unexplained_retries", 0) > 0:
            return "NOT_CERTIFIED (retry dishonesty)"
        if getattr(amp, "retry_rate", 0.0) > max_retry_rate:
            return "NOT_CERTIFIED (retry dishonesty)"
        if getattr(amp, "product_failures", 0) > 0:
            return "STOP scaling; fix product defect"
    if verdict == "CERTIFIED":
        return "PROCEED to larger-scale campaign"
    if verdict == "QUALIFIED_PARTIAL":
        return "ANALYZE infra-transience + retry honesty; do NOT scale"
    return "NOT_CERTIFIED"