"""34.9 Gate -- 8 gates, no threshold mutation."""
from __future__ import annotations
from enum import Enum
class Gate(str, Enum):
    CONSTRAINT_DETECTED="CONSTRAINT_DETECTED"; HYPOTHESIS_VALID="HYPOTHESIS_VALID"; CANDIDATE_GENERATED="CANDIDATE_GENERATED"; SEMANTIC_PRESERVED="SEMANTIC_PRESERVED"; VERIFIED="VERIFIED"; PERFORMANCE_IMPROVED="PERFORMANCE_IMPROVED"; REGRESSION_ABSENT="REGRESSION_ABSENT"; ROLLBACK_DEMONSTRATED="ROLLBACK_DEMONSTRATED"
ORDER=list(Gate)
def evaluate(evidence: dict):
    for g in ORDER:
        if not evidence.get(g.value, False):
            return (False, g)
    return (True, None)
