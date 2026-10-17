"""Deployment handoff status.

This module does not invoke a CI provider, deploy a repository, probe health,
or collect telemetry. It must not manufacture success claims in the absence
of evidence from those systems.
"""
from __future__ import annotations


def handoff_to_deployment(repo_url: str) -> dict:
    """Return an explicit not-yet-attempted handoff, never synthetic success."""
    return {
        "repo": repo_url,
        "ci": "unknown",
        "deployed": False,
        "deployment_status": "not_attempted",
        "health": "unknown",
        "telemetry": "unknown",
        "evidence": [],
        "blockers": [
            "CI execution evidence has not been supplied.",
            "No deployment operation has been executed.",
            "No health probe or telemetry source has been queried.",
        ],
    }
