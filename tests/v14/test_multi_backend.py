"""v1.4 Compiler Backend System gates — C0-C11 (multi-backend plugin boundary)."""

from __future__ import annotations

import pytest

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from compiler.core.lowering import isr_to_plan
from compiler.core.conformance import plan_element_ids, CHECKER
from compiler.core.repository import GeneratedRepository, build_repository
from compiler.composition import build_backend_registry
from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend


# ---------------------------------------------------------------------------
# Helpers
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
    return ISRRevision.create("sys", "revX", "1.0", g, Provenance(created_by="test", created_at="2025-01-01T00:00:00Z"))


# ---------------------------------------------------------------------------
# C0 — inventory
# ---------------------------------------------------------------------------

def test_c0_compiler_core_packages_exist():
    import compiler.core
    import compiler.core.plan
    import compiler.core.lowering
    import compiler.core.conformance
    import compiler.core.repository
    import compiler.core.registry
    import compiler.core.protocol


# ---------------------------------------------------------------------------
# C1 — ISR-to-plan lowering produces expected elements
# ---------------------------------------------------------------------------

def test_c1_lowering_produces_plan():
    rev = _revision()
    plan = isr_to_plan(rev)
    assert len(plan.services) == 1
    svc = plan.services[0]
    assert svc.id == "service:a"
    assert len(svc.data_models) == 1
    assert svc.data_models[0].id == "dm:core"
    assert len(svc.published_events) == 1
    assert svc.published_events[0].id == "event:e"
    assert len(plan.security) == 1
    assert plan.security[0].policy_id == "sec:p"


# ---------------------------------------------------------------------------
# C2 — plan element IDs include infra stubs
# ---------------------------------------------------------------------------

def test_c2_plan_element_ids_include_infra():
    plan = isr_to_plan(_revision())
    ids = plan_element_ids(plan)
    assert "infra:docker" in ids
    assert "infra:k8s" in ids
    assert "infra:ci" in ids
    assert "infra:readme" in ids
    assert "infra:main" in ids
    assert "infra:repositories" in ids
    assert "infra:docs" in ids
    assert "service:a" in ids
    assert "dm:core" in ids
    assert "event:e" in ids
    assert "sec:p" in ids


# ---------------------------------------------------------------------------
# C3 — PythonFastAPIBackend compiles and conforms
# ---------------------------------------------------------------------------

def test_c3_python_backend_conforms():
    plan = isr_to_plan(_revision())
    b = PythonFastAPIBackend()
    repo = b.compile(plan)
    assert isinstance(repo, GeneratedRepository)
    report = b.conformance(plan, repo)
    assert report.passed
    assert report.missing == []


# ---------------------------------------------------------------------------
# C4 — RustAxumBackend compiles and conforms
# ---------------------------------------------------------------------------

def test_c4_rust_backend_conforms():
    plan = isr_to_plan(_revision())
    b = RustAxumBackend()
    repo = b.compile(plan)
    assert isinstance(repo, GeneratedRepository)
    report = b.conformance(plan, repo)
    assert report.passed
    assert report.missing == []


# ---------------------------------------------------------------------------
# C5 — compile determinism (same plan → same hash)
# ---------------------------------------------------------------------------

def test_c5_compile_determinism():
    plan = isr_to_plan(_revision())
    for b in [PythonFastAPIBackend(), RustAxumBackend()]:
        r1 = b.compile(plan)
        r2 = b.compile(plan)
        assert r1.content_hash == r2.content_hash
        assert r1.files == r2.files


# ---------------------------------------------------------------------------
# C6 — distinct backends produce distinct repositories
# ---------------------------------------------------------------------------

def test_c6_distinct_backends_distinct_output():
    plan = isr_to_plan(_revision())
    py = PythonFastAPIBackend().compile(plan)
    rs = RustAxumBackend().compile(plan)
    assert py.content_hash != rs.content_hash
    assert set(py.files.keys()) != set(rs.files.keys())


# ---------------------------------------------------------------------------
# C7 — omission detected by conformance checker per backend
# ---------------------------------------------------------------------------

def test_c7_omission_detected():
    plan = isr_to_plan(_revision())
    for b in [PythonFastAPIBackend(), RustAxumBackend()]:
        repo = b.compile(plan)
        ep = b.element_paths(plan)
        victim = ep["service:a"]
        modified = {k: v for k, v in repo.files.items() if k != victim}
        broken = build_repository(modified)
        report = b.conformance(plan, broken)
        assert not report.passed
        assert victim in report.missing


# ---------------------------------------------------------------------------
# C8 — unmapped element detected
# ---------------------------------------------------------------------------

def test_c8_unmapped_element_detected():
    plan = isr_to_plan(_revision())
    b = PythonFastAPIBackend()
    repo = b.compile(plan)
    broken_ep: dict[str, str] = {}
    report = CHECKER.check(plan, broken_ep, repo)
    assert not report.passed
    assert any(m.startswith("unmapped:") for m in report.missing)


# ---------------------------------------------------------------------------
# C9 — registry lookup by name
# ---------------------------------------------------------------------------

def test_c9_registry_lookup():
    reg = build_backend_registry()
    assert "python-fastapi" in reg.list_names()
    assert "rust-axum" in reg.list_names()
    py = reg.get("python-fastapi")
    rs = reg.get("rust-axum")
    assert isinstance(py, PythonFastAPIBackend)
    assert isinstance(rs, RustAxumBackend)


# ---------------------------------------------------------------------------
# C10 — both backends conform and produce distinct output
# ---------------------------------------------------------------------------

def test_c10_both_backends_conform_and_differ():
    plan = isr_to_plan(_revision())
    reg = build_backend_registry()
    py = reg.get("python-fastapi")
    rs = reg.get("rust-axum")
    rpy = py.compile(plan)
    rrs = rs.compile(plan)
    assert py.conformance(plan, rpy).passed
    assert rs.conformance(plan, rrs).passed
    assert rpy.content_hash != rrs.content_hash


# ---------------------------------------------------------------------------
# C11 — compiler core does not import concrete backends (static scan)
# ---------------------------------------------------------------------------

def test_c11_core_does_not_import_backends():
    """Static proof: compiler.core modules never import compiler.backends."""
    import compiler.core.conformance
    import compiler.core.lowering
    import compiler.core.plan
    import compiler.core.protocol
    import compiler.core.registry
    import compiler.core.repository
    import os

    core_dir = os.path.dirname(compiler.core.conformance.__file__)
    violations: list[str] = []
    for fname in os.listdir(core_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(core_dir, fname)
        text = open(fpath, encoding="utf-8").read()
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "compiler.backends" in stripped or "from compiler.backends" in stripped:
                violations.append(f"{fname}:{i}: {stripped}")
    assert violations == [], f"Core imports backend: {violations}"
