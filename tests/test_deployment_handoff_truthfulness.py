from tiannara.application.publication.deployment_handoff import handoff_to_deployment


def test_unconfigured_handoff_never_claims_ci_deployment_health_or_telemetry():
    result = handoff_to_deployment("https://example.invalid/repo")

    assert result["status"] == "not_configured"
    assert result["ci"] == "not_verified"
    assert result["deployed"] is False
    assert result["health"] == "not_checked"
    assert result["telemetry"] == "not_connected"
    assert result["evidence"] == {
        "ci_run_id": None,
        "deployment_id": None,
        "health_check_ref": None,
        "telemetry_source_ref": None,
    }
    assert result["blockers"]
