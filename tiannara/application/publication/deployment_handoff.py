"""Deployment handoff status without fabricated CI or runtime claims.

No deployment provider is configured here. This function deliberately reports
that handoff has not been attempted; a real adapter must return independently
observed CI, deployment, health, and telemetry evidence before any of those
states can be marked successful.
"""
def handoff_to_deployment(repo_url: str) -> dict:
    return {
        "repo": repo_url,
        "status": "not_configured",
        "ci": "not_verified",
        "deployed": False,
        "health": "not_checked",
        "telemetry": "not_connected",
        "evidence": {
            "ci_run_id": None,
            "deployment_id": None,
            "health_check_ref": None,
            "telemetry_source_ref": None,
        },
        "blockers": [
            "No live deployment adapter is configured.",
            "CI, deployment, health, and telemetry have not been independently verified.",
        ],
    }
