"""Evidence-gated deployment handoff status.

This module reports deployment state; it does not perform CI, deploy workloads,
probe health endpoints, or collect telemetry. Unknown state must never be
presented as successful operation.
"""
from __future__ import annotations


def handoff_to_deployment(repo_url: str) -> dict:
    """Return an explicitly unverified handoff until evidence adapters exist.

    The repository URL is a locator, not evidence that CI ran or a deployment
    exists. A future provider integration must supply independently checkable
    run/deployment/health/telemetry evidence before any status can advance.
    """
    return {
        "repo": repo_url,
        "ci": "UNKNOWN",
        "deployed": False,
        "health": "UNKNOWN",
        "telemetry": "UNKNOWN",
        "verified": False,
        "blockers": [
            "CI run evidence has not been collected",
            "deployment identity and status have not been verified",
            "health probe evidence has not been collected",
            "telemetry ingestion has not been verified",
        ],
    }
