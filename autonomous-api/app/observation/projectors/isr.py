"""ISR projector (RR-01): deterministic canonical → observation mapping.

Pure function of the canonical snapshot. Sorting is MANDATORY so that
contentHash is stable across identical revisions (provenance/integrity
model depends on it).

Error contract:
- ISR store unreachable            → PLATFORM_UNAVAILABLE (503)
- ISR present but revision missing → PLATFORM_INTERNAL (500)
- Required facet missing           → PLATFORM_DEGRADED (503), facet named

503-over-fake policy retained: an unbound or partially bound ISR is
reported, never synthesized.
"""
from __future__ import annotations

from app.core.contracts.observations import (
    DeploymentTargetSummary,
    DomainSummary,
    ISRObservation,
    ServiceSummary,
)
from app.core.contracts.provenance import (
    ContractMetadata,
    ObservationProvenance,
    now_utc,
)
from app.core.exceptions import NotFoundError, ObservationDomainError
from app.core.ids import content_hash
from app.observation.projectors.base import ProjectionContract
from app.observation.projectors.isr_binding import CanonicalIsrAccessor


class IsrProjector:
    def __init__(
        self,
        *,
        accessor: CanonicalIsrAccessor,
        source_revision: str,
    ) -> None:
        self._accessor = accessor
        self._source_revision = source_revision
        # Per-revision memo: same revision → byte-identical projection.
        self._cache: dict = {}

    async def project(self) -> ISRObservation:
        isr = await self._accessor.read()
        revision = getattr(isr, "revision", None)
        if not revision:
            # Fail closed: do not fabricate a revision.
            raise NotFoundError("ISR has no revision; cannot project")

        cached = self._cache.get(revision)
        if cached is not None:
            return cached

        for facet in ("domains", "services", "deployments"):
            if not hasattr(isr, facet):
                raise ObservationDomainError(
                    f"Required ISR facet missing: {facet}",
                    code="PLATFORM_DEGRADED",
                    http_status=503,
                    context={"operation": "observation.isr",
                             "parameters": {"missingFacet": facet}},
                )

        domains = sorted(
            (
                DomainSummary(
                    name=d.name, capabilityCount=len(d.capabilities)
                )
                for d in isr.domains
            ),
            key=lambda d: d.name,
        )
        services = sorted(
            (
                ServiceSummary(id=s.id, name=s.name, domain=s.domain)
                for s in isr.services
            ),
            key=lambda s: s.id,
        )
        targets: dict = {}
        for dep in isr.deployments:
            targets.setdefault(dep.target, set()).update(dep.service_ids)
        deployment_targets = sorted(
            (
                DeploymentTargetSummary(target=t, serviceCount=len(ids))
                for t, ids in targets.items()
            ),
            key=lambda t: t.target,
        )

        body = {
            "isrRevision": revision,
            "domains": [d.model_dump() for d in domains],
            "services": [s.model_dump() for s in services],
            "deploymentTargets": [t.model_dump() for t in deployment_targets],
        }
        cid, ver = ProjectionContract.ISR
        provenance = ObservationProvenance(
            sourceRevision=self._source_revision,
            sourceSubsystem="isr",
            capturedAt=now_utc(),
            contentHash=content_hash(body),
        )
        observation = ISRObservation(
            metadata=ContractMetadata(contractId=cid, schemaVersion=ver),
            provenance=provenance,
            isrRevision=revision,
            domains=domains,
            services=services,
            deploymentTargets=deployment_targets,
        )
        self._cache[revision] = observation
        return observation