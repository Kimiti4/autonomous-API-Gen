import pytest
from app.engine.capability_verification import verification_profile
from app.engine.work_mode import WorkMode

@pytest.mark.parametrize("mode", list(WorkMode))
def test_every_bucket_two_mode_has_verification_profile(mode):
    profile = verification_profile(mode)
    assert profile.required_properties
    profile.validate_evidence({p: ("evidence",) for p in profile.required_properties})

def test_missing_capability_evidence_fails_closed():
    profile = verification_profile(WorkMode.SEO)
    with pytest.raises(ValueError, match="missing-capability-evidence:seo:crawlability"):
        profile.validate_evidence({"seo": ("e",), "metadata-correctness": ("e",), "content-integrity": ("e",)})

def test_extra_evidence_does_not_replace_required_properties():
    profile = verification_profile(WorkMode.DOCUMENT)
    with pytest.raises(ValueError, match="missing-capability-evidence:document:implementation-traceability"):
        profile.validate_evidence({"documentation-accuracy": ("e",), "unrelated": ("e",)})
