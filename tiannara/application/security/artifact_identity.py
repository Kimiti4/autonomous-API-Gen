"""34.1 Artifact Security Identity -- 7 hashes bound."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash
@dataclass(frozen=True)
class ArtifactSecurityIdentity:
    artifact_hash: str; isr_hash: str; compiler_hash: str; dependency_lock_hash: str; security_policy_hash: str; security_campaign_hash: str; generation_hash: str
    def identity(self) -> str:
        return canonical_hash({"artifact": self.artifact_hash, "isr": self.isr_hash, "compiler": self.compiler_hash, "deps": self.dependency_lock_hash, "policy": self.security_policy_hash, "campaign": self.security_campaign_hash, "generation": self.generation_hash})
    def verify(self, other: "ArtifactSecurityIdentity") -> bool:
        return self.identity() == other.identity()
