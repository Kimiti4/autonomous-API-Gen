"""Evidence-gated deployment handoff.

This module has no CI, deployment, health-check, or telemetry provider wired in.
It therefore reports unknown/blocked state rather than manufacturing success.
A future provider adapter must supply independently verifiable evidence before
this contract can report any deployment stage as successful.
"""
from __future__ import annotations


def handoff_to_deployment(repo_url: str) -> dict:
    """Return a truthful handoff state when no deployment evidence adapter exists."""
    if not isinstance(repo_url, str) or not repo_url.strip():
        raise ValueError("repo_url must be a non-empty repository reference")

    blockers = [
        "CI run evidence is unavailable",
        "deployment execution evidence is unavailable",
        "post-deployment health-check evidence is unavailable",
        "telemetry ingestion evidence is unavailable",
    ]
    return {
        "repo": repo_url,
        "status": "BLOCKED_NO_EVIDENCE",
        "ci": "unknown",
        "deployed": None,
        "health": "unknown",
        "telemetry": "unknown",
        "verified": False,
        "blockers": blockers,
    }
