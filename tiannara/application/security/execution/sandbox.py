"""33.7 Isolated sandbox -- disposable, bounded."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
@dataclass(frozen=True)
class SandboxConfig:
    network: str = "isolated"; filesystem: str = "ephemeral"; timeout_s: int = 30
@dataclass(frozen=True)
class Sandbox:
    sandbox_id: str; artifact_hash: str; config: SandboxConfig
    def execution_id(self): return hashlib.sha256(f"{self.sandbox_id}:{self.artifact_hash}".encode()).hexdigest()[:12]
    def cleanup(self): return {"cleaned": True, "sandbox_id": self.sandbox_id}
