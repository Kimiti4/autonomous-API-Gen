"""35.6 Chaos campaign -- contract-driven, not engine-authored."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class ChaosSpec: required_failures: tuple[str,...>
def is_exercised(contract, observed): return all(f in observed for f in contract.required_failures)
