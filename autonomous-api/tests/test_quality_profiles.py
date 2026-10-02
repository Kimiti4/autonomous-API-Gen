from app.engine.quality_profiles import profile_for

def test_profiles_are_distinct_and_nonempty():
    fe, be, fs = profile_for("frontend"), profile_for("backend"), profile_for("fullstack")
    assert fe.obligations and be.obligations and fs.obligations
    assert {x.obligation_id for x in fe.obligations} != {x.obligation_id for x in be.obligations}

def test_quality_is_framework_neutral():
    for role in ("frontend","backend","fullstack"):
        text = " ".join(x.statement for x in profile_for(role).obligations).lower()
        assert "react" not in text and "fastapi" not in text and "postgresql" not in text
