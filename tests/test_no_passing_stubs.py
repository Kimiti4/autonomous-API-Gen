"""PR C1/C2 — no passing stubs.

Every gate that can certify generated software must fail on hollow or
tampered artifacts and pass only on the real thing:

* conformance content floor (empty / comment-only / too-sparse / unparsable);
* OpenAPI-driven business-endpoint probing (a health-only service fails);
* independent verification in a separate process (tamper/missing fail);
* fail-closed calibration runtime gate (skips never pass);
* documentation completeness requires substance;
* SDK contract tests require parseable sources and business routes;
* the emitters provably RUN: a payroll-shaped ISR (World Concern TOR domain)
  compiles end-to-end and the emitted test suite passes.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from certification.core.metrics import _doc_completeness
from certification.stages.docker_stages import (
    RealDockerStages,
    probe_business_endpoints,
)
from compiler.composition import build_backend_registry
from compiler.core.conformance import hollow_finding
from compiler.core.lowering import isr_to_plan
from compiler.core.repository import build_repository
from compiler.models import (
    BackendCapabilities,
    BackendManifest,
    CompilationOutput,
    GeneratedArtifact,
)
from compiler.sdk.base import CompilerBackendBase
from compiler.sdk.testing import run_backend_contract_tests
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _revision() -> ISRRevision:
    g = ISRGraph(
        nodes={
            "service:a": Node(id="service:a", type=NodeType.SERVICE, properties={"label": "orders"}),
            "dm:core": Node(id="dm:core", type=NodeType.DATA_MODEL, properties={"label": "Order"}),
            "event:e": Node(id="event:e", type=NodeType.EVENT, properties={"label": "OrderCreated"}),
            "sec:p": Node(id="sec:p", type=NodeType.SECURITY_POLICY),
        },
        edges={
            "pers": Edge(id="pers", type=EdgeType.PERSISTS, source_id="service:a", target_id="dm:core"),
            "pub": Edge(id="pub", type=EdgeType.PUBLISHES, source_id="service:a", target_id="event:e"),
            "sec": Edge(id="sec", type=EdgeType.SECURED_BY, source_id="service:a", target_id="sec:p"),
        },
    )
    return ISRRevision.create(
        "test", "rev", "1.0", g,
        Provenance(created_by="test", created_at="2025-01-01T00:00:00Z"),
    )


def _payroll_revision() -> ISRRevision:
    """The World Concern payroll TOR expressed as a technology-free ISR.

    Employee management, payroll processing, statutory compliance, payslip
    distribution, reporting, and employee self-service — 16 entities, 4
    published events, one security policy.
    """
    layout = {
        "employees": (
            "employee_management",
            ["Employee", "Department", "Position", "EmployeeBankAccount"],
            ["EmployeeOnboarded"],
        ),
        "payroll": (
            "payroll_processing",
            ["PayrollRun", "Payslip", "Allowance", "Deduction", "LoanAdvance"],
            ["PayrollRunCompleted"],
        ),
        "statutory": (
            "statutory_compliance",
            ["TaxRule", "StatutoryReturn"],
            [],
        ),
        "distribution": (
            "payslip_distribution",
            ["PayslipDelivery"],
            ["PayslipIssued"],
        ),
        "reporting": (
            "payroll_reporting",
            ["PayrollSummary", "BankTransferSchedule"],
            [],
        ),
        "ess": (
            "employee_self_service",
            ["LeaveRequest", "LeaveBalance"],
            ["LeaveRequested"],
        ),
    }
    nodes: dict[str, Node] = {}
    edges: dict[str, Edge] = {}
    n = 0
    for key, (label, entities, events) in layout.items():
        svc = f"service:{key}"
        nodes[svc] = Node(id=svc, type=NodeType.SERVICE, properties={"label": label})
        for ent in entities:
            n += 1
            nid = f"dm:{key}:{ent}"
            nodes[nid] = Node(id=nid, type=NodeType.DATA_MODEL, properties={"label": ent})
            edges[f"edge:{n}"] = Edge(
                id=f"edge:{n}", type=EdgeType.PERSISTS, source_id=svc, target_id=nid,
            )
        for ev in events:
            n += 1
            nid = f"event:{key}:{ev}"
            nodes[nid] = Node(id=nid, type=NodeType.EVENT, properties={"label": ev})
            edges[f"edge:{n}"] = Edge(
                id=f"edge:{n}", type=EdgeType.PUBLISHES, source_id=svc, target_id=nid,
            )
    nodes["sec:rbac"] = Node(id="sec:rbac", type=NodeType.SECURITY_POLICY)
    n += 1
    edges[f"edge:{n}"] = Edge(
        id=f"edge:{n}", type=EdgeType.SECURED_BY,
        source_id="service:payroll", target_id="sec:rbac",
    )
    g = ISRGraph(nodes=nodes, edges=edges)
    return ISRRevision.create(
        "payroll", "rev", "1.0", g,
        Provenance(created_by="test", created_at="2025-01-01T00:00:00Z"),
    )


# ---------------------------------------------------------------------------
# Conformance content floor
# ---------------------------------------------------------------------------

def test_conformance_rejects_comment_only_element():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("python-fastapi")
    repo = backend.compile(plan)

    stubbed = dict(repo.files)
    stubbed["app/main.py"] = "# TODO: implement the application\n"
    report = backend.conformance(plan, build_repository(stubbed))

    assert report.passed is False
    assert "hollow:app/main.py:comment-only" in report.missing


def test_conformance_rejects_unparsable_element():
    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("python-fastapi")
    repo = backend.compile(plan)

    stubbed = dict(repo.files)
    stubbed["app/main.py"] = "def broken(:\n    pass\n"
    report = backend.conformance(plan, build_repository(stubbed))

    assert report.passed is False
    assert any(m.startswith("syntax:app/main.py") for m in report.missing)


def test_hollow_finding_content_floor():
    assert hollow_finding("x.txt", "   ") == "hollow:x.txt:empty"
    assert hollow_finding("x.py", "# nothing here\n") == "hollow:x.py:comment-only"
    assert hollow_finding("x.py", "x = 1\n") == "hollow:x.py:too-sparse"
    assert (
        hollow_finding("x.py", "def f():\n    return 'a substantive implementation'\n")
        is None
    )


# ---------------------------------------------------------------------------
# Business-endpoint probe (health-only services cannot pass)
# ---------------------------------------------------------------------------

class _SpecHandler(BaseHTTPRequestHandler):
    server_version = "stub/1.0"

    def do_GET(self):
        spec = getattr(self.server, "spec", {})
        statuses = getattr(self.server, "statuses", {})
        if self.path == "/health":
            self._send(200, b'{"status": "ok"}')
        elif self.path == "/openapi.json":
            self._send(200, json.dumps(spec).encode("utf-8"))
        elif self.path in statuses:
            self._send(statuses[self.path], b"[]")
        else:
            self._send(404, b"not found")

    def _send(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return


@contextmanager
def _http_service(spec: dict, statuses: dict | None = None):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _SpecHandler)
    httpd.spec = spec
    httpd.statuses = statuses or {}
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_probe_business_endpoints_rejects_health_only_service():
    with _http_service({"paths": {"/health": {"get": {}}}}) as port:
        ok, detail, err = probe_business_endpoints(port, timeout=2)
    assert ok is False
    assert "no business GET endpoints" in detail
    assert err == ""


def test_probe_business_endpoints_accepts_live_business_routes():
    spec = {
        "paths": {
            "/health": {"get": {}},
            "/api/orders": {"get": {}},
            "/api/orders/{item_id}": {"get": {}},
        }
    }
    with _http_service(spec, {"/api/orders": 200}) as port:
        ok, detail, err = probe_business_endpoints(port, timeout=2)
    assert ok is True
    assert "/api/orders:200" in detail
    assert err == ""


def test_probe_business_endpoints_accepts_auth_protected_routes():
    spec = {"paths": {"/api/orders": {"get": {}}}}
    with _http_service(spec, {"/api/orders": 401}) as port:
        ok, _, _ = probe_business_endpoints(port, timeout=2)
    assert ok is True


def test_probe_business_endpoints_rejects_server_errors():
    spec = {"paths": {"/api/orders": {"get": {}}}}
    with _http_service(spec, {"/api/orders": 500}) as port:
        ok, detail, err = probe_business_endpoints(port, timeout=2)
    assert ok is False
    assert "status=500" in detail
    assert err == ""


def test_probe_stage_fails_health_only_container(monkeypatch):
    import certification.stages.docker_stages as ds

    monkeypatch.setattr(ds, "_run", lambda cmd, timeout=900: (0, "0.1%/1MB"))
    with _http_service({"paths": {"/health": {"get": {}}}}) as port:
        se = RealDockerStages().probe(port, "cid-noop")
    assert se.passed is False
    assert se.failure_class == "product"
    assert "probe FAILED" in se.detail


def test_probe_stage_passes_with_live_business_surface(monkeypatch):
    import certification.stages.docker_stages as ds

    monkeypatch.setattr(ds, "_run", lambda cmd, timeout=900: (0, "0.1%/1MB"))
    spec = {"paths": {"/api/orders": {"get": {}}}}
    with _http_service(spec, {"/api/orders": 200}) as port:
        se = RealDockerStages().probe(port, "cid-noop")
    assert se.passed is True
    assert se.failure_class == ""
    assert se.startup_polls == 0
    assert "business=" in se.detail


# ---------------------------------------------------------------------------
# Independent verification (separate process, disk-recomputed hashes)
# ---------------------------------------------------------------------------

def test_independent_verify_accepts_authentic_and_rejects_tampering(tmp_path):
    from certification.campaign.campaign_b import _run_independent_verify

    plan = isr_to_plan(_revision())
    backend = build_backend_registry().get("python-fastapi")
    ident = backend.identity()
    repo = backend.compile(plan)
    conf = backend.conformance(plan, repo)

    repo_dir = tmp_path / "candidate"
    for path, content in repo.files.items():
        full = repo_dir / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")

    ok, out = _run_independent_verify(repo, plan, ident, conf, repo_dir=str(repo_dir))
    assert ok is True, out

    target = repo_dir / "app" / "main.py"
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8"
    )
    ok, _ = _run_independent_verify(repo, plan, ident, conf, repo_dir=str(repo_dir))
    assert ok is False

    target.unlink()
    ok, _ = _run_independent_verify(repo, plan, ident, conf, repo_dir=str(repo_dir))
    assert ok is False


# ---------------------------------------------------------------------------
# Documentation completeness requires substance
# ---------------------------------------------------------------------------

def test_doc_completeness_requires_substance():
    assert _doc_completeness({}) == 0.0
    assert _doc_completeness({"README.md": "# Title\n"}) == 0.0
    assert _doc_completeness(
        {"README.md": "# Title\n\nTODO\n", "docs/architecture.md": "# Arch\n"}
    ) == 0.0
    filled = {
        "README.md": "# Title\n\n" + "Real documentation body. " * 8 + "\n",
        "docs/architecture.md": "# Arch\n\n" + "Layered architecture notes. " * 8 + "\n",
    }
    assert _doc_completeness(filled) == 1.0


# ---------------------------------------------------------------------------
# SDK contract tests: parseable sources + business routes
# ---------------------------------------------------------------------------

def _artifact_backend(files: dict[str, str]) -> CompilerBackendBase:
    class _Emitter(CompilerBackendBase):
        manifest = BackendManifest(
            backend_id="test.emitter",
            name="Test Emitter",
            version="0.1.0",
            description="Emits the given artifacts verbatim.",
            capabilities=BackendCapabilities(
                supported_targets=["test"],
                artifact_types=["text"],
            ),
        )

        def compile(self, context):
            return CompilationOutput(
                artifacts=[
                    GeneratedArtifact(path=p, content=c) for p, c in files.items()
                ]
            )

    return _Emitter()


_HEALTH_ONLY_APP = (
    "from fastapi import FastAPI\n"
    "\n"
    "app = FastAPI()\n"
    "\n"
    "@app.get('/health')\n"
    "def health():\n"
    "    return {'status': 'ok'}\n"
)

_REAL_CRUD_APP = _HEALTH_ONLY_APP + (
    "\n"
    "@app.get('/api/items')\n"
    "def list_items():\n"
    "    return []\n"
)


def test_contract_tests_reject_unparsable_sources():
    backend = _artifact_backend({"app/main.py": "def broken(:\n    pass\n"})
    passed, results, _ = run_backend_contract_tests(backend)
    by_name = {r.name: r for r in results}
    assert passed is False
    assert by_name["sources_parse"].passed is False


def test_contract_tests_reject_health_only_fastapi_app():
    backend = _artifact_backend({"app/main.py": _HEALTH_ONLY_APP})
    passed, results, _ = run_backend_contract_tests(backend)
    by_name = {r.name: r for r in results}
    assert passed is False
    assert by_name["business_routes_present"].passed is False


def test_contract_tests_accept_real_crud_app():
    backend = _artifact_backend({"app/main.py": _REAL_CRUD_APP})
    passed, results, _ = run_backend_contract_tests(backend)
    assert passed, [(r.name, r.message) for r in results if not r.passed]


# ---------------------------------------------------------------------------
# Payroll end-to-end: the emitted Python application runs its own tests
# ---------------------------------------------------------------------------

def test_payroll_isr_compiles_to_a_running_tested_python_app(tmp_path):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")

    plan = isr_to_plan(_payroll_revision())
    backend = build_backend_registry().get("python-fastapi")
    repo = backend.compile(plan)

    report = backend.conformance(plan, repo)
    assert report.passed, report.missing

    for path, content in repo.files.items():
        full = tmp_path / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = (proc.stdout + proc.stderr)[-3000:]
    assert proc.returncode == 0, tail
    assert " passed" in proc.stdout


def test_payroll_rust_emission_is_wired_with_business_routes():
    plan = isr_to_plan(_payroll_revision())
    backend = build_backend_registry().get("rust-axum")
    repo = backend.compile(plan)

    report = backend.conformance(plan, repo)
    assert report.passed, report.missing

    main = repo.files["src/main.rs"]
    assert "async fn health" in main
    assert "#[cfg(test)]" in main and "#[test]" in main
    assert "assert!(true" not in main
    assert 'include_str!("../openapi.json")' in main
    assert "/api/employees" in main
    assert "/api/payrollruns" in main

    spec = json.loads(repo.files["openapi.json"])
    assert "/api/employees" in spec["paths"]
    assert "/api/employees/{item_id}" in spec["paths"]
    assert "/api/events/PayrollRunCompleted" in spec["paths"]

    assert "pub mod Employee;" in repo.files["src/domain/mod.rs"]
    assert "pub mod PayrollRun;" in repo.files["src/domain/mod.rs"]
