from pathlib import Path
from pydantic import BaseModel, Field

from .capability_manifest import CapabilityContractError, CapabilityManifest


class SystemDeploymentBundle(BaseModel):
    """A compiled artifact of an evolved software design."""

    project_id: str
    backend_name: str
    isr_hash: str
    path: Path
    artifacts: list[str] = Field(default_factory=list)

    #: Capability manifest emitted by the compiler backend. `None` during the
    #: migration window; capability-driven meta-compilers call
    #: `require_capability_manifest`, which fails loudly on absence — absence
    #: is never silently treated as "no capabilities".
    capability_manifest: CapabilityManifest | None = None

    model_config = {"arbitrary_types_allowed": True}


def require_capability_manifest(
    bundle: "SystemDeploymentBundle",
) -> CapabilityManifest:
    if bundle.capability_manifest is None:
        raise CapabilityContractError(
            f"bundle '{bundle.project_id}' carries no capability manifest; "
            "capability-driven meta-compilation requires one"
        )
    return bundle.capability_manifest
