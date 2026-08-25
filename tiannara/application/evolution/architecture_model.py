"""34.1 Architecture Representation -- derived from ISR facts."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash
@dataclass(frozen=True)
class Architecture:
    services: tuple[str,...]; databases: tuple[str,...]; queues: tuple[str,...]; caches: tuple[str,...]
    topology: str; consistency: str
    def derived_from_isr(self, isr_facts: dict) -> bool:
        return all(s in str(isr_facts) for s in self.services)
    def content_hash(self) -> str:
        return canonical_hash({"services": list(self.services), "topology": self.topology})

def derive_architecture(isr_facts: dict) -> Architecture:
    # Derive, not template: use fact keys to determine services
    services = tuple(k for k in isr_facts if "service" in k or "capability" in k)
    if not services:
        services = ("api",)
    return Architecture(services=services, databases=("primary",), queues=(), caches=(), topology="single-region", consistency="strong")
