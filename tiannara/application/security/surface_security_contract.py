"""33.10 Parameterized surface -- contract declares, engine evaluates."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class SurfaceRequirement: class_id: str; allowed: tuple[str,...]; required: tuple[str,...]
@dataclass(frozen=True)
class SurfaceContract: required_classes: tuple[str,...]; requirements: dict
CONTRACT = SurfaceContract(("strong","weak"), {"strong": SurfaceRequirement("strong", ("CERTIFIED",), ("CERTIFIED",)), "weak": SurfaceRequirement("weak", ("NOT_CERTIFIED",), ("NOT_CERTIFIED",))})
def evaluate(contract, observed): return all(any(o==r for o in observed.get(c,[])) for c,r in contract.requirements.items())
