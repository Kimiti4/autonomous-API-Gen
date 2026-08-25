"""33.9 Discrimination -- ISR mutations before compile."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class Mutation: mutation_id: str; defect: str
MUTATIONS = (Mutation("sql-inj","SQL injection"), Mutation("xss","XSS"), Mutation("ssrf","SSRF"))
def mutate_isr(isr, mut): return type("D",(),{"isr": isr, "mutation": mut, "source_hash": "abc"})()
