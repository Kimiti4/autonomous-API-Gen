import uuid
from typing import Any

from constitutional_architecture.engine.mutations.base import MutationOperator
from constitutional_architecture.isr.model.deployment import Deployment
from constitutional_architecture.isr.model.isr import ISR, ISRProvenance
from constitutional_architecture.isr.model.system import System


class AddCacheMutation(MutationOperator):
    identifier = "performance_add_cache"
    description = "Introduce caching for an entity by adding deployment-level caching metadata"

    def apply(self, isr: ISR, target_id: str, params: dict[str, Any] | None = None) -> ISR:
        params = params or {}
        ent_id = target_id.replace("ent:", "")
        deployment = Deployment(
            id=params.get("deployment_id", f"cache-{uuid.uuid4().hex[:8]}"),
            name=f"Cache-{ent_id}",
            description=f"Caching layer for entity '{ent_id}' (strategy={params.get('strategy', 'write_through')}, TTL={params.get('ttl_seconds', 300)}s)",
        )

        modules = list(isr.system.modules)
        for mi, mod in enumerate(modules):
            if any(e.id == ent_id for e in mod.entities):
                modules[mi] = mod
                return ISR(
                    system=System(
                        id=isr.system.id, name=isr.system.name,
                        modules=tuple(modules),
                        deployment=deployment,
                    ),
                    version=isr.version + 1,
                    provenance=ISRProvenance(
                        parent_hash=isr.content_hash,
                        mutation_description=f"Added caching deployment for entity '{ent_id}'",
                    ),
                )
        return isr
