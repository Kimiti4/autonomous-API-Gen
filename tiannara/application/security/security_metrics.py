"""33.8 Security Metrics -- observations only, no composite."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class SecurityMetrics:
    attack_count: int; blocked: int; detected: int; contained: int; missed: int; bounded: int
    detection_rate: float; false_positive_rate: float; false_negative_rate: float
    @property
    def conserved(self): return self.blocked+self.detected+self.missed+self.bounded==self.attack_count
    def block_rate(self): return self.blocked/self.attack_count if self.attack_count else 0
