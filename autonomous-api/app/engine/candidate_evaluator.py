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
from app.engine.docker_runner import DockerRunner
from app.engine.fitness import calculate_fitness
from app.engine.genome import Genome


def _hash_genome(genome: Genome) -> str:
    payload = json.dumps(genome.encode(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _runtime_score(health_ok: bool, openapi_ok: bool, auth_boundary_ok: bool, crud_ok: bool) -> float:
    return round((0.30 if health_ok else 0.0) + (0.25 if openapi_ok else 0.0) + (0.20 if auth_boundary_ok else 0.0) + (0.25 if crud_ok else 0.0), 3)


def evaluate_candidate(genome: Genome, *, use_docker: bool = True, output_dir: str = "output/candidates") -> dict[str, Any]:
    """Build a candidate and collect observed evidence.

    Runtime mode is fail-closed: a build or probe failure never falls back to
    synthetic fitness. Static scoring is available only when explicitly asked
    for with ``use_docker=False``.
    """
    genome_hash = _hash_genome(genome)
    candidate_dir = os.path.join(output_dir, genome_hash[:16])
    evidence = {
        "candidate_id": genome.genome_id,
        "genome_hash": genome_hash,
        "artifact_path": candidate_dir,
        "evaluation_mode": "static" if not use_docker else "runtime_failed",
        "build_ok": False,
        "health_ok": False,
        "openapi_ok": False,
        "auth_boundary_ok": False,
        "crud_ok": False,
        "runtime_score": 0.0 if use_docker else None,
        "static_score": calculate_fitness(genome) if not use_docker else None,
        "error": None,
    }
    try:
        build_genome_output(genome, candidate_dir)
        evidence["build_ok"] = True
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
            evidence["health_ok"] = health.status_code == 200
            openapi = client.get(f"{base}/openapi.json")
            evidence["openapi_ok"] = openapi.status_code == 200 and isinstance(openapi.json(), dict)

            if genome.services:
                service_url = f"{base}/api/{genome.api_version}/{genome.services[0]}/"
                anonymous = client.get(service_url)
                evidence["auth_boundary_ok"] = anonymous.status_code in {401, 403}
                headers = {}
                auth_kwargs = {}
                if genome.auth == "api_key":
                    headers["X-API-Key"] = "evaluator-test-key"
                elif genome.auth in {"jwt", "oauth2"}:
                    import jwt
                    headers["Authorization"] = "Bearer " + jwt.encode({"sub": "evaluator"}, "evaluator-test-secret", algorithm="HS256")
                elif genome.auth == "basic":
                    auth_kwargs["auth"] = ("evaluator", "evaluator-password")
                created = client.post(service_url, json={"name": "evaluator", "description": "runtime probe"}, headers=headers, **auth_kwargs)
                evidence["crud_ok"] = created.status_code == 201

        evidence["evaluation_mode"] = "runtime"
        evidence["runtime_score"] = _runtime_score(evidence["health_ok"], evidence["openapi_ok"], evidence["auth_boundary_ok"], evidence["crud_ok"])
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
