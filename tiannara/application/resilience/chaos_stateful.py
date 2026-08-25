"""35.6 Chaos stateful/replay -- stateful, replay, resource pressure."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass
class ChaosState:
    counter: int = 0
    history: tuple = ()
    def replay(self):
        return self.history
    def step(self, event: str):
        object.__setattr__(self, "counter", self.counter + 1)
        object.__setattr__(self, "history", (*self.history, event))
        return self.counter
    def under_pressure(self, limit: int) -> bool:
        return self.counter > limit
