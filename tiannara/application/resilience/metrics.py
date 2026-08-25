"""35.5 Metrics -- no composite."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class ResilienceMetrics:
    injected: int; detected: int; contained: int; recovered: int; missed: int; bounded: int
    time_to_detect: float; time_to_contain: float; time_to_recover: float
    @property
    def conserved(self): return self.detected+self.missed+self.bounded <= self.injected
    def has_composite(self): return False
