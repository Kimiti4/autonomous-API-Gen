from app.engine.engineering_quality import (
    EngineeringDiscipline, quality_profile, review_quality,
)


def test_frontend_profile_requires_senior_frontend_concerns():
    ids = {o.obligation_id for o in quality_profile(EngineeringDiscipline.FRONTEND).obligations}
    assert {"FE-ARCH", "FE-UX", "FE-A11Y", "FE-STATE", "FE-PERF", "FE-SEC", "FE-TEST", "FE-RES"} <= ids


def test_backend_profile_requires_senior_backend_concerns():
    ids = {o.obligation_id for o in quality_profile(EngineeringDiscipline.BACKEND).obligations}
    assert {"BE-DOMAIN", "BE-CONTRACT", "BE-DATA", "BE-SEC", "BE-REL", "BE-PERF", "BE-OBS", "BE-TEST"} <= ids


def test_fullstack_composes_both_disciplines_and_adds_integration():
    ids = {o.obligation_id for o in quality_profile(EngineeringDiscipline.FULLSTACK).obligations}
    assert "FE-A11Y" in ids and "BE-REL" in ids and "FS-CONTRACT" in ids


def test_quality_is_obligation_based_not_style_based():
    findings = review_quality(EngineeringDiscipline.FRONTEND, {"FE-ARCH", "FE-UX"})
    assert any("FE-A11Y" in x for x in findings)
