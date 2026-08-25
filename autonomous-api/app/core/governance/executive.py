"""Executive + Constitution gate model (§9 gaps)."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Executive:
    executiveId: str = "executive"
    quorumThreshold: float = 0.6

CONSTITUTION_GATE = {
    "gateId": "constitution-compliance",
    "category": "constitution",
    "description": "Machine-checkable encoding of the Tiannara Constitution",
}
