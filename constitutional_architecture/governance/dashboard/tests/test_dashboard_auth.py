"""
Phase 28 — Milestone 5A spec §15.4.1: dashboard authentication and
authorization tests (tasks 5A.1–5A.4).

Covers: session login/logout, unauthenticated blocking, CSRF enforcement on
every mutation, the role→permission matrix (viewer/auditor/approver/
operator/admin), kernel-level denial surfacing, and fail-closed 503s.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from constitutional_architecture.governance.dashboard.app import create_app
from constitutional_architecture.governance.dashboard.client import (
    GovernanceDashboardClient,
)
from constitutional_architecture.governance.dashboard.config import DashboardConfig
from constitutional_architecture.governance.dashboard.render_console import (
    build_demo_kernel,
)


# ── sessions ─────────────────────────────────────────────────────────────

def test_unauthenticated_pages_redirect_to_login(tc):
    for path in (
        "/",
        "/constitutions",
        "/policy-sets",
        "/evaluations",
        "/approvals",
        "/exceptions",
        "/audit",
        "/audit/integrity",
        "/lineage",
        "/metrics",
    ):
        r = tc.get(path, follow_redirects=False)
        assert r.status_code in (303, 401), f"{path} must not be reachable anonymously"


def test_unauthenticated_mutations_rejected(tc, pending_approval):
    r = tc.post(
        f"/approvals/{pending_approval}/approve",
        data={"csrf_token": "x", "comment": "go"},
        follow_redirects=False,
    )
    assert r.status_code == 401


def test_login_sets_session_cookie_and_logout_clears(tc, login):
    login("bob")
    assert "gov_session" in tc.cookies
    r = tc.get("/", follow_redirects=True)
    assert r.status_code == 200
    tc.post("/logout", follow_redirects=False)
    assert "gov_session" not in tc.cookies
    assert tc.get("/", follow_redirects=False).status_code in (303, 401)


def test_login_with_bad_credentials_fails(tc):
    r = tc.post(
        "/login", data={"username": "bob", "password": "wrong"}, follow_redirects=False
    )
    assert r.status_code in (200, 401)
    assert "gov_session" not in tc.cookies


def test_login_page_is_public(tc):
    assert tc.get("/login").status_code == 200


def test_session_identity_appears_in_nav(tc, login):
    login("carol")
    body = tc.get("/approvals").text
    assert "carol" in body


# ── CSRF ─────────────────────────────────────────────────────────────────

def test_mutation_without_csrf_is_rejected(tc, login, pending_approval):
    login("carol")
    r = tc.post(
        f"/approvals/{pending_approval}/approve",
        data={"comment": "go"},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_mutation_with_wrong_csrf_is_rejected(tc, login, csrf, pending_approval):
    login("carol")
    csrf(f"/approvals/{pending_approval}")  # fetch a real token
    r = tc.post(
        f"/approvals/{pending_approval}/reject",
        data={"comment": "no", "csrf_token": "not-the-token"},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_mutation_with_valid_csrf_succeeds(tc, login, csrf, pending_approval):
    login("carol")
    token = csrf(f"/approvals/{pending_approval}")
    r = tc.post(
        f"/approvals/{pending_approval}/approve",
        data={"comment": "approved", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_csrf_token_differs_between_sessions(tc, login, csrf):
    login("bob")
    first = csrf("/approvals")
    tc.post("/logout", follow_redirects=False)
    login("carol")
    second = csrf("/approvals")
    assert first != second


# ── role → permission matrix ─────────────────────────────────────────────

def test_viewer_cannot_approve(tc, login, csrf, pending_approval):
    login("bob")
    token = csrf(f"/approvals/{pending_approval}")
    r = tc.post(
        f"/approvals/{pending_approval}/approve",
        data={"comment": "go", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_viewer_cannot_revoke_exception(tc, login, csrf, active_exception):
    login("bob")
    token = csrf(f"/exceptions/{active_exception.id}")
    r = tc.post(
        f"/exceptions/{active_exception.id}/revoke",
        data={"justification": "nope", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_viewer_cannot_verify_integrity(tc, login, csrf):
    login("bob")
    token = csrf("/audit/integrity")
    r = tc.post("/audit/integrity/verify", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 403


def test_approver_cannot_revoke_exception(tc, login, csrf, active_exception):
    login("carol")
    token = csrf(f"/exceptions/{active_exception.id}")
    r = tc.post(
        f"/exceptions/{active_exception.id}/revoke",
        data={"justification": "nope", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_approver_cannot_verify_integrity(tc, login, csrf):
    login("carol")
    token = csrf("/audit/integrity")
    r = tc.post("/audit/integrity/verify", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 403


def test_auditor_can_verify_integrity(tc, login, csrf):
    login("alice")
    token = csrf("/audit/integrity")
    r = tc.post("/audit/integrity/verify", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 200


def test_operator_can_revoke_exception(tc, login, csrf, active_exception):
    login("alice")
    token = csrf(f"/exceptions/{active_exception.id}")
    r = tc.post(
        f"/exceptions/{active_exception.id}/revoke",
        data={"justification": "resolved", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_admin_can_approve(tc, login, csrf, pending_approval):
    login("dave")
    token = csrf(f"/approvals/{pending_approval}")
    r = tc.post(
        f"/approvals/{pending_approval}/approve",
        data={"comment": "ok", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303


# ── kernel authorization stays authoritative ─────────────────────────────

def test_kernel_denial_is_surfaced_as_403():
    """Dashboard permission passes but the kernel-side actor role is not
    authorized → the dashboard must surface the kernel denial."""
    config = DashboardConfig()
    config.kernel_role_map["governance_approver"] = ("unrelated_role",)
    kernel = build_demo_kernel()
    app = create_app(GovernanceDashboardClient(kernel), config=config)
    tc = TestClient(app)
    tc.post("/login", data={"username": "carol", "password": "carol-pw"}, follow_redirects=True)

    import re

    from constitutional_architecture.governance.testing import make_approval_request

    evaluation = kernel.evaluate(make_approval_request(subject_id="kernel_denial_probe"))
    kernel.create_approvals(evaluation)
    pid = [a.id for a in kernel.approvals.all_approvals() if a.status.value == "PENDING"][0]
    m = re.search(r'name="csrf_token" value="([^"]+)"', tc.get(f"/approvals/{pid}").text)
    r = tc.post(
        f"/approvals/{pid}/approve",
        data={"comment": "go", "csrf_token": m.group(1)},
        follow_redirects=False,
    )
    assert r.status_code == 403
    assert "Kernel denied" in r.text


# ── fail closed ──────────────────────────────────────────────────────────

def test_kernel_unavailable_fails_closed():
    app = create_app(GovernanceDashboardClient(None))
    tc = TestClient(app)
    tc.post("/login", data={"username": "bob", "password": "bob-pw"}, follow_redirects=True)
    r = tc.get("/approvals")
    assert r.status_code == 503
    assert "unavailable" in r.text.lower()


def test_kernel_unavailable_on_mutation_fails_closed():
    app = create_app(GovernanceDashboardClient(None))
    tc = TestClient(app)
    tc.post("/login", data={"username": "alice", "password": "alice-pw"}, follow_redirects=True)
    import re

    m = re.search(r'name="csrf-token" content="([^"]*)"', tc.get("/approvals").text)
    r = tc.post("/exceptions/x/revoke", data={"justification": "j", "csrf_token": m.group(1)}, follow_redirects=False)
    assert r.status_code == 503
