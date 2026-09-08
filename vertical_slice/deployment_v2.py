"""VS-D16 deployment contract (selected evolved impl: vs1-impl-v2, loopback).

Controlled test/development bring-up of the exact D15-generated
implementation under the exact D14-selected architecture. Consumes upstream
authority read-only; creates none. Deterministic except for explicitly
recorded runtime-instance identifiers (bound port, process id, timestamps),
which are audit-only and never influence pass/fail semantics.

Deployment glue only: no observation campaign, no evidence interpretation,
no hypothesis update, no evolution work (see §§22–23).
"""

from __future__ import annotations

import hashlib
import json

DEPLOYMENT_CONTRACT_VERSION = "vs1-deploy-v2"
DEPLOYMENT_ID = "vs1-deploy-v2"

# Frozen D15 implementation identity (verified, never regenerated here).
IMPLEMENTATION_ID = "vs1-impl-v2"
IMPLEMENTATION_HASH = (
    "d2090df69127e9922494bb7a4d526de087fd948ee793bdf326d5fe18fac1dd8c"
)
PARENT_IMPLEMENTATION_ID = "vs1-impl-v1"

# Frozen D14 selection identity.
ARCHITECTURE_ID = "vs1-evolved-96fe2d29fd76"
ARCHITECTURE_HASH = (
    "d0f8d7579a08de83e9490f373e6f1df70d44a546a1a8385cd27444516f724631"
)
SELECTION_ID = "vs1-selection-44cf7da052a5"
SELECTION_HASH = (
    "f39c508e3a6ed52dbdd1b57766706804277e4cf70d12509f71f589370f549d1b"
)
EVOLUTION_ID = "vs1-evolution-synthetic-001"
OBJECTIVE_ID = "vs1-objective-synthetic-auth-boundary"
AUTHORIZATION_ID = "vs1-authorization-synthetic-001"

# Frozen constitutional inputs.
ISR_HASH = "48e53dcef47aad84e52e20ec116f5b1f9616a626f42d1c281e3cc26cdf8e9dfb"
GRAPH_HASH = "28548494e754e9b8214e9f72511a7ba0187fa3378264306a82ff8868bd2e5526"
REAL_DECISION = "NO_CHANGE"
REAL_DECISION_HASH = "ae6df7c889ff9cab"

# Synthetic-test-only authority (never production).
AUTHORIZATION_MODE = "SYNTHETIC_TEST_ONLY"
PRODUCTION_AUTHORIZATION = False
DEPLOYMENT_SCOPE = "controlled_test"

TARGET = "local-uvicorn-loopback"
HOST = "127.0.0.1"
DEFAULT_PORT = 8472

LAUNCH_MODULE = "vertical_slice.serve_v2"
STARTUP_COMMAND = ["python", "-m", LAUNCH_MODULE]
ENTRYPOINT = "vertical_slice/app_v2/api.py:create_app"
ENTRYPOINT_NAMESPACE = "vertical_slice.app_v2"
READINESS_PATH = "/health"
READINESS_STATUS = 200
SHUTDOWN_METHOD = "SIGTERM/terminate + wait"

DATABASE_KIND = "json-file-store"
DATABASE_CONFIG = "VS1_STORE_DIR (per-deployment isolated directory)"
RUNTIME_ENVIRONMENT = "local python process (python 3.14.0)"
SECURITY_CONFIG = "v2 central AuthorizationPolicy active; no bypass flags"
LOGGING_CONFIG = "uvicorn stdio (audit only; not scraped by D16)"

# Pinned at VS-D16 execution time (same backend generation as D05/D15).
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
    "api-reachability",
    "valid-request",
    "expected-rejection",
    "persistence-connectivity",
    "response-serialization",
    "security-bring-up",
    "shutdown-clean",
    "restart-deterministic",
)

# D16 must never write to these upstream paths (firewall, §29).
UPSTREAM_GUARD_PATHS: tuple[str, ...] = (
    "folder/VS1_REQUIREMENTS.md",
    "folder/VS1_ISR.md",
    "folder/VS1_CANDIDATES.md",
    "folder/VS1_IMPLEMENTATION.md",
    "folder/VS1_EVOLUTION_SELECTION.md",
    "folder/VS1_REGENERATION.md",
    "vertical_slice/isr.py",
    "vertical_slice/candidates.py",
    "vertical_slice/regeneration.py",
)


class DeploymentError(Exception):
    """Fail-closed deployment-gate failure."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def runtime_configuration() -> dict[str, object]:
    """Explicit deterministic runtime configuration identity (no secrets)."""
    return {
        "host": HOST,
        "default_port": DEFAULT_PORT,
        "application_entrypoint": ENTRYPOINT,
        "entrypoint_namespace": ENTRYPOINT_NAMESPACE,
        "launch_module": LAUNCH_MODULE,
        "startup_command": list(STARTUP_COMMAND),
        "database_kind": DATABASE_KIND,
        "database_configuration": DATABASE_CONFIG,
        "runtime_environment": RUNTIME_ENVIRONMENT,
        "runtime_version": RUNTIME_VERSION,
        "dependency_versions": [
            {"name": n, "version": v, "purpose": p, "required": r}
            for n, v, p, r in DEPENDENCY_VERSIONS
        ],
        "security_configuration": SECURITY_CONFIG,
        "logging_configuration": LOGGING_CONFIG,
        "readiness": {"path": READINESS_PATH, "status": READINESS_STATUS},
        "shutdown": {"method": SHUTDOWN_METHOD},
    }


def build_contract() -> dict[str, object]:
    """Deterministic deployment contract (no instance identifiers)."""
    return {
        "deployment_contract_version": DEPLOYMENT_CONTRACT_VERSION,
        "deployment_id": DEPLOYMENT_ID,
        "deployment_scope": DEPLOYMENT_SCOPE,
        "implementation_id": IMPLEMENTATION_ID,
        "implementation_hash": IMPLEMENTATION_HASH,
        "parent_implementation_id": PARENT_IMPLEMENTATION_ID,
        "architecture_id": ARCHITECTURE_ID,
        "architecture_hash": ARCHITECTURE_HASH,
        "selection_id": SELECTION_ID,
        "selection_hash": SELECTION_HASH,
        "evolution_id": EVOLUTION_ID,
        "objective_id": OBJECTIVE_ID,
        "authorization_id": AUTHORIZATION_ID,
        "isr_hash": ISR_HASH,
        "graph_hash": GRAPH_HASH,
        "real_decision": REAL_DECISION,
        "real_decision_hash": REAL_DECISION_HASH,
        "deployment_target": TARGET,
        "runtime_configuration_identity": runtime_configuration(),
        "authorization_mode": AUTHORIZATION_MODE,
        "production_authorization": PRODUCTION_AUTHORIZATION,
        "smoke_tests": list(SMOKE_TESTS),
    }


def normalize_contract(contract: dict[str, object]) -> dict[str, object]:
    """Normalized deployment description: instance-free by construction.

    The contract contains no PIDs, timestamps, or bound ports, so
    normalization is the identity function — stated explicitly so the
    determinism claim is auditable rather than implicit.
    """
    return json.loads(_canon(contract))


def contract_hash(contract: dict[str, object] | None = None) -> str:
    return _sha(_canon(normalize_contract(build_contract() if contract is None else contract)))


def verify_implementation() -> dict[str, str]:
    """The v2 component set exists and the policy delta is represented."""
    import vertical_slice.app_v2.api as api
    import vertical_slice.app_v2.policy as policy
    import vertical_slice.app_v2.service as service

    if not hasattr(policy, "AuthorizationPolicy"):
        raise DeploymentError("central policy boundary missing")
    for name in ("check_session", "check_member", "check_admin"):
        if not hasattr(policy.AuthorizationPolicy, name):
            raise DeploymentError(f"policy decision missing: {name}")
    if service.TaskTrackerServiceV2.__module__ != "vertical_slice.app_v2.service":
        raise DeploymentError("service is not the v2 namespace")
    import inspect as _inspect
    _source = _inspect.getsource(service.TaskTrackerServiceV2)
    if "AuthorizationPolicy" not in _source or "self._policy" not in _source:
        raise DeploymentError("service does not delegate to the policy boundary")
    if not hasattr(api, "create_app"):
        raise DeploymentError("v2 entrypoint missing")
    return {
        "implementation_id": IMPLEMENTATION_ID,
        "entrypoint": ENTRYPOINT,
        "namespace": ENTRYPOINT_NAMESPACE,
        "policy": "AuthorizationPolicy(check_session,check_member,check_admin)",
    }


EVIDENCE_SECTIONS: tuple[str, ...] = (
    "identity",
    "integrity",
    "configuration",
    "startup",
    "readiness",
    "api_reachability",
    "controlled_smoke",
    "security_bring_up",
    "shutdown",
    "restart",
    "determinism",
    "authorization_status",
    "boundary_status",
    "provenance",
)

PROVENANCE_FIELDS: tuple[str, ...] = (
    "result",
    "deployment_id",
    "implementation_id",
    "implementation_hash",
    "architecture_id",
    "architecture_hash",
    "selection_hash",
    "isr_hash",
    "deployment_contract",
    "deployment_target",
    "test_identity",
    "generated_at",
)


def assemble_evidence(live: dict[str, object], generated_at: str) -> dict[str, object]:
    """Assemble canonical evidence; only `generated_at` is audit-only.

    `live` carries the recorded bring-up results (startup, readiness, …).
    The normalized hash covers everything except `generated_at`, so the
    content identity is recomputable independently of wall-clock time.
    """
    contract = build_contract()
    for section in EVIDENCE_SECTIONS:
        if section in ("provenance", "configuration"):
            continue  # derived inside assemble, not a live input
        if section not in live:
            raise DeploymentError(f"evidence missing section: {section}")
    evidence: dict[str, object] = {
        "deployment_contract_version": DEPLOYMENT_CONTRACT_VERSION,
        "identity": live["identity"],
        "integrity": live["integrity"],
        "configuration": runtime_configuration(),
        "startup": live["startup"],
        "readiness": live["readiness"],
        "api_reachability": live["api_reachability"],
        "controlled_smoke": live["controlled_smoke"],
        "security_bring_up": live["security_bring_up"],
        "shutdown": live["shutdown"],
        "restart": live["restart"],
        "determinism": {
            "canonical_contract": contract_hash(contract),
            "repeated_preparation": live["determinism"],
        },
        "authorization_status": live["authorization_status"],
        "boundary_status": live["boundary_status"],
        "provenance": {
            "result": live.get("result", "PASS"),
            "deployment_id": DEPLOYMENT_ID,
            "implementation_id": IMPLEMENTATION_ID,
            "implementation_hash": IMPLEMENTATION_HASH,
            "architecture_id": ARCHITECTURE_ID,
            "architecture_hash": ARCHITECTURE_HASH,
            "selection_hash": SELECTION_HASH,
            "isr_hash": ISR_HASH,
            "deployment_contract": DEPLOYMENT_CONTRACT_VERSION,
            "deployment_target": TARGET,
            "test_identity": "tests/vs1/test_deployment_v2.py",
            "generated_at": generated_at,
        },
    }
    _normalized = {k: v for k, v in evidence.items() if k != "provenance"}
    _provenance = evidence["provenance"]
    assert isinstance(_provenance, dict)
    _normalized["provenance"] = {
        k: v for k, v in _provenance.items() if k != "generated_at"}
    evidence["normalized_hash"] = _sha(_canon(_normalized))
    return evidence


def verify_upstream() -> dict[str, str]:
    """Recompute frozen upstream identities D01–D15 (fail-closed, read-only)."""
    from vertical_slice import implementation as IMPL
    from vertical_slice import regeneration as REG

    identity = IMPL.frozen_input_identity()
    if identity["vs-d01-graph-sha256"] != GRAPH_HASH:
        raise DeploymentError("D01 graph drift")
    if identity["vs-d02-isr-content-hash"] != ISR_HASH:
        raise DeploymentError("D02 ISR drift")
    if identity.get("implementation-version") != PARENT_IMPLEMENTATION_ID:
        raise DeploymentError("D04 implementation drift")
    evidence = REG.build_evidence()
    if evidence["implementation_id"] != IMPLEMENTATION_ID:
        raise DeploymentError("D15 implementation drift")
    if evidence["implementation_hash"] != IMPLEMENTATION_HASH:
        raise DeploymentError("D15 implementation hash drift")
    if evidence["selected_architecture_id"] != ARCHITECTURE_ID:
        raise DeploymentError("D14 winner drift")
    if evidence["selected_architecture_hash"] != ARCHITECTURE_HASH:
        raise DeploymentError("D14 architecture drift")
    if evidence["selection_hash"] != SELECTION_HASH:
        raise DeploymentError("D14 selection hash drift")
    if evidence["isr_hash"] != ISR_HASH:
        raise DeploymentError("ISR drift")
    if evidence.get("production_authorization") is not False:
        raise DeploymentError("production authorization drift")
    with open("vertical_slice/evolution_decision_v2_evidence.json",
              encoding="utf-8") as f:
        real_decision = json.load(f)
    if real_decision.get("decision") != REAL_DECISION:
        raise DeploymentError("real D12 decision drift")
    return {
        "d01_graph": GRAPH_HASH,
        "d02_isr": ISR_HASH,
        "d04_implementation": PARENT_IMPLEMENTATION_ID,
        "d12_decision": REAL_DECISION,
        "d14_architecture": ARCHITECTURE_ID,
        "d14_selection_hash": SELECTION_HASH,
        "d15_implementation": IMPLEMENTATION_ID,
        "d15_implementation_hash": IMPLEMENTATION_HASH,
    }
