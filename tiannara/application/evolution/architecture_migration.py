"""34.6 Migration -- plan, intermediate, compatibility, rollback."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class MigrationPlan:
    steps: tuple[str,...]; intermediate: str; compatibility: str; rollback: str
    def has_rollback(self): return bool(self.rollback)
def compile_migration(transformation, hypothesis) -> MigrationPlan:
    return MigrationPlan(steps=("plan","migrate","verify"), intermediate="intermediate-arch", compatibility="compat-layer", rollback=hypothesis.rollback)
