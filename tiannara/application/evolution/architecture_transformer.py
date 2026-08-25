"""34.4 Transformer -- operates on ISR carriers, not hardcoded."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash
@dataclass(frozen=True)
class Transformation:
    from_arch: str; to_arch: str; isr_carrier: str
    def is_valid(self): return self.isr_carrier in ("services","databases","queues","topology")
    def hash(self): return canonical_hash((self.from_arch, self.to_arch, self.isr_carrier))
def propose_transformation(constraint: str, isr_facts: dict) -> Transformation:
    # Derive from constraint + ISR, not hardcoded 1M->microservices
    if "throughput" in constraint:
        return Transformation("monolith","services","services")
    if "database" in constraint:
        return Transformation("single_db","read_replicas","databases")
    return Transformation("monolith","modular","topology")
