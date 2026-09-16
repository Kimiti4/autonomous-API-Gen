"""Evidence extraction for generated capability claims."""
from __future__ import annotations

import os
from typing import Any

from app.engine.capability_contract import assess_genome
from app.engine.genome import Genome


def _result(name: str, requested: bool, verified: bool, checks: dict[str, bool], reason: str = "") -> dict[str, Any]:
    return {"requested": requested, "verified": bool(requested and verified), "checks": checks, "reason": reason}


def inspect_artifact(genome: Genome, artifact_dir: str) -> dict[str, Any]:
    """Verify capability-specific generated artifacts without executing them."""
    results: dict[str, Any] = {}
    main_path = os.path.join(artifact_dir, "main.py")
    security_path = os.path.join(artifact_dir, "security.py")
    requirements_path = os.path.join(artifact_dir, "requirements.txt")
    main_text = open(main_path, encoding="utf-8").read() if os.path.isfile(main_path) else ""
    security_text = open(security_path, encoding="utf-8").read() if os.path.isfile(security_path) else ""
    requirements_text = open(requirements_path, encoding="utf-8").read() if os.path.isfile(requirements_path) else ""
    contract = {item.name: item for item in assess_genome(genome)}

    service_files_ok = all(os.path.isfile(os.path.join(artifact_dir, "services", f"{service}.py")) for service in genome.services)
    results["services"] = _result("services", contract["services"].requested, service_files_ok, {"service_files": service_files_ok})
    db_ok = os.path.isfile(os.path.join(artifact_dir, "database.py")) and os.path.isfile(requirements_path)
    results["database"] = _result("database", contract["database"].requested, db_ok, {"database_file": os.path.isfile(os.path.join(artifact_dir, "database.py")), "requirements_file": os.path.isfile(requirements_path)})
    auth_ok = os.path.isfile(security_path) and "def require_auth" in security_text
    results["authentication"] = _result("authentication", contract["authentication"].requested, auth_ok, {"security_file": os.path.isfile(security_path), "require_auth": "def require_auth" in security_text})
    cors_ok = "CORSMiddleware" in main_text
    results["cors"] = _result("cors", contract["cors"].requested, cors_ok, {"middleware": cors_ok})
    health_present = '@app.get("/health")' in main_text
    results["health_endpoints"] = _result("health_endpoints", contract["health_endpoints"].requested, health_present == genome.health_endpoints, {"selection_fidelity": health_present == genome.health_endpoints})
    results["openapi"] = _result("openapi", contract["openapi"].requested, os.path.isfile(main_path), {"main_file": os.path.isfile(main_path)})
    version_ok = f'/api/{genome.api_version}/' in main_text
    results["api_version"] = _result("api_version", contract["api_version"].requested, version_ok, {"route_prefix": version_ok})
    rate_ok = ("rate_limit_middleware" in main_text and "RATE_LIMIT_REQUESTS_PER_MINUTE" in main_text) if genome.rate_limiting else "rate_limit_middleware" not in main_text
    results["rate_limiting"] = _result("rate_limiting", contract["rate_limiting"].requested, rate_ok, {"selection_fidelity": rate_ok})
    metrics_ok = ("http_requests_total" in main_text and '@app.get("/metrics")' in main_text) if genome.metrics_endpoints else '@app.get("/metrics")' not in main_text
    results["metrics_endpoints"] = _result("metrics_endpoints", contract["metrics_endpoints"].requested, metrics_ok, {"selection_fidelity": metrics_ok})
    if genome.tracing_enabled:
        tracing_checks = {
            "opentelemetry_api": "from opentelemetry import trace" in main_text,
            "tracer_provider": "TracerProvider" in main_text,
            "asgi_instrumentation": "OpenTelemetryMiddleware" in main_text,
            "trace_id_header": 'response.headers["X-Trace-ID"]' in main_text,
            "requirements": "opentelemetry-sdk" in requirements_text and "opentelemetry-instrumentation-asgi" in requirements_text,
        }
        tracing_ok = all(tracing_checks.values())
    else:
        tracing_checks = {"selection_fidelity": "OpenTelemetryMiddleware" not in main_text}
        tracing_ok = tracing_checks["selection_fidelity"]
    results["tracing"] = _result("tracing", contract["tracing"].requested, tracing_ok, tracing_checks)
    if genome.timeout_config:
        try:
            timeout_value = float(genome.timeout_config.get("request_timeout", 0))
            timeout_checks = {
                "middleware": "request_timeout_middleware" in main_text,
                "wait_for": "asyncio.wait_for" in main_text,
                "configured_value": f"REQUEST_TIMEOUT_SECONDS = {timeout_value!r}" in main_text,
                "timeout_response": 'status_code=504' in main_text and '"Request timed out"' in main_text,
            }
            timeout_ok = timeout_value > 0 and all(timeout_checks.values())
        except (TypeError, ValueError):
            timeout_checks = {"valid_configuration": False}
            timeout_ok = False
        results["timeout_config"] = _result("timeout_config", contract["timeout_config"].requested, timeout_ok, timeout_checks, contract["timeout_config"].reason)
    else:
        timeout_checks = {"selection_fidelity": "request_timeout_middleware" not in main_text}
        results["timeout_config"] = _result("timeout_config", False, timeout_checks["selection_fidelity"], timeout_checks)
    if genome.retry_policy:
        retry_checks = {
            "middleware": "class RetryPolicyMiddleware" in main_text,
            "registered": "app.add_middleware(RetryPolicyMiddleware)" in main_text,
            "retryable_statuses": "RETRYABLE_STATUS_CODES" in main_text and "502, 503, 504" in main_text,
            "bounded_attempts": "RETRY_MAX_ATTEMPTS" in main_text,
            "backoff": "RETRY_BACKOFF_MULTIPLIER" in main_text and "RETRY_MAX_DELAY" in main_text,
            "idempotent_only": 'scope.get("method") not in {"GET", "HEAD", "OPTIONS"}' in main_text,
            "probe": '@app.get("/__capability_probe__/retry")' in main_text,
        }
        retry_ok = all(retry_checks.values())
    else:
        retry_checks = {"selection_fidelity": "retry_policy_middleware" not in main_text}
        retry_ok = retry_checks["selection_fidelity"]
    results["retry_policy"] = _result("retry_policy", contract["retry_policy"].requested, retry_ok, retry_checks, contract["retry_policy"].reason)

    for item in contract.values():
        if item.name not in results and item.requested:
            results[item.name] = _result(item.name, True, False, {}, item.reason)
    return results


def summarize(results: dict[str, Any]) -> dict[str, Any]:
    requested = [name for name, value in results.items() if value["requested"]]
    verified = [name for name, value in results.items() if value["verified"]]
    failed = [name for name in requested if name not in verified]
    return {"requested": requested, "verified": verified, "failed_or_unverified": failed, "coverage": round(len(verified) / len(requested), 3) if requested else 1.0}
