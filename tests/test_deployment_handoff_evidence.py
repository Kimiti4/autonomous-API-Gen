from tiannara.application.publication.deployment_handoff import handoff_to_deployment


def test_deployment_handoff_does_not_invent_ci_deployment_health_or_telemetry():
    result = handoff_to_deployment("https://example.invalid/org/repo")

    assert result["repo"] == "https://example.invalid/org/repo"
    assert result["ci"] == "UNKNOWN"
    assert result["deployed"] is False
    assert result["health"] == "UNKNOWN"
    assert result["telemetry"] == "UNKNOWN"
    assert result["verified"] is False
    assert len(result["blockers"]) == 4
