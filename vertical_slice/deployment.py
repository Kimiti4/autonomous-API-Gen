"""VS-D05 deployment contract (selected: vs1-candidate-a, local loopback).

Deterministic except for explicitly recorded runtime-instance identifiers
(bound port, process id). Timestamps, where retained, are audit-only and
never influence pass/fail semantics.
"""

from __future__ import annotations

DEPLOYMENT_CONTRACT_VERSION = "vs1-deploy-v1"
DEPLOYMENT_ID = "vs1-local-loopback"
CANDIDATE_ID = "vs1-candidate-a"
IMPLEMENTATION_VERSION = "vs1-impl-v1"

TARGET = "local-uvicorn-loopback"
HOST = "127.0.0.1"
DEFAULT_PORT = 8471

STARTUP_COMMAND = ["python", "-m", "vertical_slice.serve"]
READINESS_PATH = "/health"
READINESS_STATUS = 200
SHUTDOWN_METHOD = "SIGTERM/terminate + wait"

# Pinned at VS-D05 execution time (see folder/VS1_DEPLOYMENT.md §6).
RUNTIME_VERSION = "3.14.0"
DEPENDENCY_VERSIONS: tuple[tuple[str, str, str, str], ...] = (
    # (name, version, purpose, required)
    ("fastapi", "0.136.0", "HTTP interface layer", "required"),
    ("uvicorn", "0.45.0", "local ASGI server", "required"),
    ("starlette", "installed", "ASGI toolkit (fastapi dependency)", "required"),
    ("httpx", "0.28.1", "test client transport", "test-only"),
    ("pydantic", "2.13.0", "contract validation", "required"),
)

SMOKE_TESTS: tuple[str, ...] = (
    "startup-readiness",
    "register-login",
    "task-crud-lifecycle",
    "assign-members",
    "unauthenticated-rejected",
    "tenant-isolation",
    "admin-only-membership",
    "durability-across-restart",
    "events-persisted",
    "shutdown-clean",
)


def build_contract() -> dict[str, object]:
    """Deterministic deployment contract (no instance identifiers)."""
    return {
        "deployment_contract_version": DEPLOYMENT_CONTRACT_VERSION,
        "deployment_id": DEPLOYMENT_ID,
        "candidate_id": CANDIDATE_ID,
        "implementation_version": IMPLEMENTATION_VERSION,
        "target": TARGET,
        "host": HOST,
        "default_port": DEFAULT_PORT,
        "runtime_version": RUNTIME_VERSION,
        "dependency_versions": [
            {"name": n, "version": v, "purpose": p, "required": r}
            for n, v, p, r in DEPENDENCY_VERSIONS
        ],
        "startup_command": list(STARTUP_COMMAND),
        "readiness": {"path": READINESS_PATH, "status": READINESS_STATUS},
        "shutdown": {"method": SHUTDOWN_METHOD},
        "smoke_tests": list(SMOKE_TESTS),
        "vs-d01-graph-sha256": "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526",
        "vs-d02-isr-content-hash": "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb",
        "vs-d03-policy": "vs1-selection-v1",
    }
