import pytest
from dataclasses import dataclass, field
from app.core.ids import content_hash
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

def _sample_isr(revision="rev-1"):
    return _Isr(revision, [_Domain("alpha", [object()])], [_Service("svc-a", "A", "alpha")], [])

@pytest.mark.asyncio
async def test_isr_projection_hash_is_recomputable():
    accessor = _Accessor(_sample_isr("rev-1"))
    isr_projector = IsrProjector(accessor=accessor, source_revision="rev1")
    obs = await isr_projector.project()
    body = {
        "isrRevision": obs.isrRevision,
        "domains": [d.model_dump() for d in obs.domains],
        "services": [s.model_dump() for s in obs.services],
        "deploymentTargets": [t.model_dump() for t in obs.deploymentTargets],
    }
    assert obs.provenance.contentHash == content_hash(body)
    assert len(obs.provenance.contentHash) == 64
    assert obs.provenance.sourceRevision
    assert obs.provenance.capturedAt

@pytest.mark.asyncio
async def test_hash_changes_when_content_changes():
    a_isr = _sample_isr("rev-1")
    b_isr = _sample_isr("rev-2")
    a = await IsrProjector(accessor=_Accessor(a_isr), source_revision="rev1").project()
    b = await IsrProjector(accessor=_Accessor(b_isr), source_revision="rev1").project()
    assert a.provenance.contentHash != b.provenance.contentHash
