"""RR-01 acceptance: IsrProjector determinism, sorting, fail-closed."""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.core.exceptions import NotFoundError
from app.observation.projectors.isr import IsrProjector


@dataclass
class _Domain:
    name: str
    capabilities: list = field(default_factory=list)


@dataclass
class _Service:
    id: str
    name: str
    domain: str


@dataclass
class _Deployment:
    target: str
    service_ids: list


@dataclass
class _Isr:
    revision: str
    domains: list
    services: list
    deployments: list


class _Accessor:
    def __init__(self, isr):
        self._isr = isr

    async def current_revision(self) -> str:
        return getattr(self._isr, "revision", "")

    async def read(self):
        return self._isr


def _sample_isr(revision="rev-1", *, unsorted=False):
    domains = [
        _Domain("zeta", [object(), object()]),
        _Domain("alpha", [object()]),
    ]
    services = [
        _Service("svc-b", "B", "alpha"),
        _Service("svc-a", "A", "zeta"),
    ]
    if not unsorted:
        domains.reverse()
        services.reverse()
    return _Isr(
        revision=revision,
        domains=domains,
        services=services,
        deployments=[
            # Duplicate service ids across deployment entries → dedup.
            _Deployment("docker", ["svc-a", "svc-b", "svc-a"]),
            _Deployment("k8s", ["svc-a"]),
        ],
    )


@pytest.fixture()
def fake_accessor():
    return _Accessor(_sample_isr())


@pytest.fixture()
def fake_accessor_unsorted():
    return _Accessor(_sample_isr(unsorted=True))


@pytest.fixture()
def empty_accessor():
    return _Accessor(_Isr("", [], [], []))


@pytest.mark.asyncio
async def test_projection_is_deterministic_for_same_revision(fake_accessor):
    p = IsrProjector(accessor=fake_accessor, source_revision="rev1")
    a = await p.project()
    b = await p.project()
    assert a.provenance.contentHash == b.provenance.contentHash


@pytest.mark.asyncio
async def test_domains_and_services_are_sorted(fake_accessor_unsorted):
    p = IsrProjector(
        accessor=fake_accessor_unsorted, source_revision="rev1"
    )
    obs = await p.project()
    assert [d.name for d in obs.domains] == sorted(
        d.name for d in obs.domains
    )
    assert [s.id for s in obs.services] == sorted(
        s.id for s in obs.services
    )
    assert [t.target for t in obs.deploymentTargets] == sorted(
        t.target for t in obs.deploymentTargets
    )


@pytest.mark.asyncio
async def test_missing_revision_fails_closed(empty_accessor):
    p = IsrProjector(accessor=empty_accessor, source_revision="rev1")
    with pytest.raises(NotFoundError):
        await p.project()


@pytest.mark.asyncio
async def test_deployment_targets_deduplicate_services(fake_accessor):
    p = IsrProjector(accessor=fake_accessor, source_revision="rev1")
    obs = await p.project()
    docker = next(
        t for t in obs.deploymentTargets if t.target == "docker"
    )
    assert docker.serviceCount == 2  # svc-a + svc-b, deduplicated


@pytest.mark.asyncio
async def test_projection_carries_contract_and_provenance(fake_accessor):
    p = IsrProjector(accessor=fake_accessor, source_revision="rev1")
    obs = await p.project()
    assert obs.metadata.contractId == "platform.observation.isr"
    assert obs.metadata.schemaVersion == "1.0.0"
    assert obs.isrRevision == "rev-1"
    assert len(obs.provenance.contentHash) == 64
    assert obs.provenance.sourceSubsystem == "isr"


@pytest.mark.asyncio
async def test_cache_invalidates_on_revision_change():
    isr = _sample_isr("rev-1")
    accessor = _Accessor(isr)
    p = IsrProjector(accessor=accessor, source_revision="rev1")
    a = await p.project()
    isr.revision = "rev-2"  # canonical state changed
    b = await p.project()
    assert a.isrRevision == "rev-1"
    assert b.isrRevision == "rev-2"