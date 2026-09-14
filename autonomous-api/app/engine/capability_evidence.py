"""Evidence extraction for generated capability claims.

A capability is not considered verified merely because a genome requested it or
because the builder emitted a file. This module records deterministic artifact
and runtime observations so candidate acceptance can remain fail-closed.
"""
from __future__ import annotations

import os
from typing import Any

from app.engine.capability_contract import assess_genome
from app.engine.genome import Genome


def _result(name: str, requested: bool, verified: bool, checks: dict[str, bool], reason: str = "") -> dict[str, Any]:
    return {
        "requested": requested,
        "verified": bool(requested and verified),
        "checks": checks,
        "reason": reason,
    }


def inspect_artifact(genome: Genome, artifact_dir: str) -> dict[str, Any]:
    """Verify capability-specific generated artifacts without executing them."""
    results: dict[str, Any] = {}
    files = {
        "main": os.path.join(artifact_dir, "main.py"),
        "database": os.path.join(artifact_dir, "database.py"),
        "security": os.path.join(artifact_dir, "security.py"),
        "requirements": os.path.join(artifact_dir, "requirements.txt"),
        "dockerfile": os.path.join(artifact_dir, "Dockerfile"),
    }
    text = ""
    if os.path.isfile(files["main"]):
        with open(files["main"], encoding="utf-8") as handle:
            text = handle.read()

    contract = {item.name: item for item in assess_genome(genome)}
    results["services"] = _result(
        "services", contract["services"].requested,
        all(os.path.isfile(os.path.join(artifact_dir, "services", f"{service}.py")) for service in genome.services),
        {"service_files": all(os.path.isfile(os.path.join(artifact_dir, "services", f"{service}.py")) for service in genome.services)},
    )
    results["database"] = _result(
        "database", contract["database"].requested,
        os.path.isfile(files["database"]) and os.path.isfile(files["requirements"]),
        {"database_file": os.path.isfile(files["database"]), "requirements_file": os.path.isfile(files["requirements"])},
    )
    results["authentication"] = _result(
        "authentication", contract["authentication"].requested,
        os.path.isfile(files["security"]) and "require_auth" in open(files["security"], encoding="utf-8").read(),
        {"security_file": os.path.isfile(files["security"]), "require_auth": os.path.isfile(files["security"]) and "require_auth" in open(files["security"], encoding="utf-8").read()},
    )
    results["cors"] = _result("cors", contract["cors"].requested, "CORSMiddleware" in text, {"middleware": "CORSMiddleware" in text})
    health_present = '@app.get("/health")' in text
    results["health_endpoints"] = _result(
        "health_endpoints", contract["health_endpoints"].requested,
        health_present == genome.health_endpoints,
        {"selection_fidelity": health_present == genome.health_endpoints},
    )
    results["openapi"] = _result("openapi", contract["openapi"].requested, os.path.isfile(files["main"]), {"main_file": os.path.isfile(files["main"])})
    results["api_version"] = _result("api_version", contract["api_version"].requested, f'/api/{genome.api_version}/' in text, {"route_prefix": f'/api/{genome.api_version}/' in text})

    # Explicitly record requested-but-unimplemented capabilities. These must
    # never become verified through generic file or runtime observations.
    for item in contract.values():
        if item.name not in results and item.requested:
            results[item.name] = _result(item.name, True, False, {}, item.reason)
    return results


def summarize(results: dict[str, Any]) -> dict[str, Any]:
    requested = [name for name, value in results.items() if value["requested"]]
    verified = [name for name, value in results.items() if value["verified"]]
    failed = [name for name in requested if name not in verified]
    return {
        "requested": requested,
        "verified": verified,
        "failed_or_unverified": failed,
        "coverage": round(len(verified) / len(requested), 3) if requested else 1.0,
    }
