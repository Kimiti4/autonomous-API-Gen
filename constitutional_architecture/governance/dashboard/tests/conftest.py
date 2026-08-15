"""
Phase 28 — Governance Dashboard web tests (Milestone 5A, spec §15.4).

Shared fixtures: demo kernel, dashboard client, BFF app, TestClient,
login/CSRF helpers, and a PENDING approval factory.
"""

from __future__ import annotations

import re

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
from constitutional_architecture.governance.testing import make_approval_request


@pytest.fixture()
def kernel():
    return build_demo_kernel()


@pytest.fixture()
def client(kernel):
    return GovernanceDashboardClient(kernel)


@pytest.fixture()
def app(client):
    return create_app(client)


@pytest.fixture()
def tc(app):
    return TestClient(app)


@pytest.fixture()
def login(tc):
    def _login(username: str = "bob", password: str = None):
        password = password or f"{username}-pw"
        r = tc.post("/login", data={"username": username, "password": password}, follow_redirects=False)
        assert r.status_code == 303, f"login failed for {username}: {r.status_code}"
        return r

    return _login


@pytest.fixture()
def csrf(tc):
    def _csrf(path: str = "/approvals"):
        m = re.search(r'name="csrf-token" content="([^"]*)"', tc.get(path).text)
        if m and m.group(1):
            return m.group(1)
        m = re.search(r'name="csrf_token" value="([^"]+)"', tc.get(path).text)
        assert m, f"no CSRF token rendered on {path}"
        return m.group(1)

    return _csrf


@pytest.fixture()
def pending_approval(kernel, client):
    evaluation = kernel.evaluate(make_approval_request(subject_id="test_proposal"))
    kernel.create_approvals(evaluation)
    ids = [a.id for a in client.list_approvals() if a.status == "PENDING"]
    assert ids, "expected at least one PENDING approval"
    return ids[0]


@pytest.fixture()
def active_exception(client):
    exceptions = [e for e in client.list_exceptions() if e.status == "ACTIVE"]
    assert exceptions, "demo kernel must contain an ACTIVE exception"
    return exceptions[0]
