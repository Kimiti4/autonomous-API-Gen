"""Runtime validation for generated API candidates."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from typing import Any

import httpx

from app.core.logger import logger
from app.engine.builder import build_genome_output
from app.engine.capability_evidence import inspect_artifact, summarize
from app.engine.docker_runner import DockerRunner
from app.engine.fitness import calculate_fitness
from app.engine.genome import Genome


def _hash_genome(genome: Genome) -> str:
    payload = json.dumps(genome.encode(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _runtime_score(health_ok: bool, openapi_ok: bool, auth_boundary_ok: bool, crud_ok: bool, contract_ok: bool) -> float:
    return round(
        (0.20 if health_ok else 0.0)
        + (0.20 if openapi_ok else 0.0)
        + (0.20 if auth_boundary_ok else 0.0)
        + (0.30 if crud_ok else 0.0)
        + (0.10 if contract_ok else 0.0),
        3,
    )


def _verify_crud(client: httpx.Client, service_url: str, headers: dict[str, str], auth_kwargs: dict[str, Any]) -> tuple[bool, dict[str, bool]]:
    checks = {
        "create": False,
        "list": False,
        "read": False,
        "update": False,
        "delete": False,
        "not_found": False,
        "validation": False,
    }
    created = client.post(service_url, json={"name": "evaluator", "description": "runtime probe"}, headers=headers, **auth_kwargs)
    checks["create"] = created.status_code == 201
    if not checks["create"]:
        return False, checks
    payload = created.json()
    item_id = payload.get("id")
    if not isinstance(item_id, int):
        return False, checks

    listed = client.get(service_url, headers=headers, **auth_kwargs)
    checks["list"] = listed.status_code == 200 and any(item.get("id") == item_id for item in listed.json().get("items", []))

    fetched = client.get(f"{service_url}{item_id}", headers=headers, **auth_kwargs)
    checks["read"] = fetched.status_code == 200 and fetched.json().get("id") == item_id

    updated = client.put(
        f"{service_url}{item_id}",
        json={"name": "evaluator-updated", "description": "updated probe"},
        headers=headers,
        **auth_kwargs,
    )
    checks["update"] = updated.status_code == 200 and updated.json().get("name") == "evaluator-updated"

    missing = client.get(f"{service_url}999999999", headers=headers, **auth_kwargs)
    checks["not_found"] = missing.status_code == 404

    invalid = client.post(service_url, json={"description": "missing required name"}, headers=headers, **auth_kwargs)
    checks["validation"] = invalid.status_code == 422

    deleted = client.delete(f"{service_url}{item_id}", headers=headers, **auth_kwargs)
    checks["delete"] = deleted.status_code == 204
    return all(checks.values()), checks


def evaluate_candidate(genome: Genome, *, use_docker: bool = True, output_dir: str = "output/candidates") -> dict[str, Any]:
    """Build a candidate and collect observed artifact/runtime evidence.

    Runtime mode is fail-closed: a build or probe failure never falls back to
    synthetic fitness. Static scoring is available only when explicitly asked
    for with ``use_docker=False``.
    """
    genome_hash = _hash_genome(genome)
    candidate_dir = os.path.join(output_dir, genome_hash[:16])
    evidence: dict[str, Any] = {
        "candidate_id": genome.genome_id,
        "genome_hash": genome_hash,
        "artifact_path": candidate_dir,
        "evaluation_mode": "static" if not use_docker else "runtime_failed",
        "build_ok": False,
        "health_ok": False,
        "openapi_ok": False,
        "auth_boundary_ok": False,
        "crud_ok": False,
        "crud_checks": {},
        "contract_ok": False,
        "artifact_capabilities": {},
        "capability_evidence": {},
        "runtime_score": 0.0 if use_docker else None,
        "static_score": calculate_fitness(genome) if not use_docker else None,
        "error": None,
    }
    try:
        build_genome_output(genome, candidate_dir)
        evidence["build_ok"] = True
        evidence["artifact_capabilities"] = inspect_artifact(genome, candidate_dir)
        evidence["capability_evidence"] = summarize(evidence["artifact_capabilities"])
    except Exception as exc:
        evidence["error"] = f"candidate build failed: {exc}"
        logger.error("Candidate build failed", exc_info=True)
        return evidence

    if not use_docker:
        return evidence

    runner = DockerRunner()
    container_name = f"evo-eval-{genome_hash[:12]}"
    try:
        success, port, error = runner.build_and_run(
            candidate_dir,
            container_name=container_name,
            environment={
                "DATABASE_URL": "sqlite:///./generated.db",
                "API_KEY": "evaluator-test-key",
                "JWT_SECRET": "evaluator-test-secret",
                "BASIC_USER": "evaluator",
                "BASIC_PASSWORD": "evaluator-password",
            },
        )
        if not success:
            evidence["error"] = error or "candidate container failed to start"
            return evidence

        base = f"http://127.0.0.1:{port}"
        with httpx.Client(timeout=10.0) as client:
            health = client.get(f"{base}/health")
            evidence["health_ok"] = (health.status_code == 200) if genome.health_endpoints else health.status_code == 404

            openapi = client.get(f"{base}/openapi.json")
            if openapi.status_code == 200:
                spec = openapi.json()
                expected_prefix = f"/api/{genome.api_version}/"
                expected_paths = {expected_prefix + f"{service}/" for service in genome.services}
                actual_paths = {path for path in spec.get("paths", {}) if path.startswith(expected_prefix)}
                evidence["openapi_ok"] = isinstance(spec, dict) and expected_paths.issubset(actual_paths)

            if genome.services:
                service_url = f"{base}/api/{genome.api_version}/{genome.services[0]}/"
                anonymous = client.get(service_url)
                evidence["auth_boundary_ok"] = anonymous.status_code in {401, 403}
                headers: dict[str, str] = {}
                auth_kwargs: dict[str, Any] = {}
                if genome.auth == "api_key":
                    headers["X-API-Key"] = "evaluator-test-key"
                elif genome.auth == "jwt":
                    import jwt
                    token = jwt.encode({"sub": "evaluator"}, "evaluator-test-secret", algorithm="HS256")
                    headers["Authorization"] = f"Bearer {token}"
                elif genome.auth == "basic":
                    auth_kwargs["auth"] = ("evaluator", "evaluator-password")
                evidence["crud_ok"], evidence["crud_checks"] = _verify_crud(client, service_url, headers, auth_kwargs)

            artifact_verified = evidence["capability_evidence"].get("failed_or_unverified", [])
            evidence["contract_ok"] = not artifact_verified

        evidence["evaluation_mode"] = "runtime"
        evidence["runtime_score"] = _runtime_score(
            evidence["health_ok"], evidence["openapi_ok"], evidence["auth_boundary_ok"], evidence["crud_ok"], evidence["contract_ok"]
        )
        if evidence["runtime_score"] < 1.0:
            evidence["error"] = evidence["error"] or "runtime contract probes did not fully pass"
        return evidence
    except Exception as exc:
        logger.error("Candidate runtime evaluation failed", exc_info=True)
        evidence["error"] = str(exc)
        return evidence
    finally:
        runner.stop_container(container_name)


async def evaluate_candidate_async(genome: Genome, *, use_docker: bool = True, output_dir: str = "output/candidates") -> dict[str, Any]:
    """Run blocking build/runtime checks off the event loop."""
    return await asyncio.to_thread(evaluate_candidate, genome, use_docker=use_docker, output_dir=output_dir)
