"""
Phase 28 — Milestone 5A spec §15.4.5: audit integrity tests (task 5A.2).

The hash chain verifies as VALID on a live kernel; tampering with any event
is detected and the first broken event is reported. Re-verification is a
privileged POST and fails closed without the kernel.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from constitutional_architecture.governance.dashboard.app import create_app
from constitutional_architecture.governance.dashboard.client import (
    GovernanceDashboardClient,
)
from constitutional_architecture.governance.dashboard.render_console import (
    build_demo_kernel,
)


@pytest.fixture()
def bob(tc, login):
    login("bob")
    return tc


def test_chain_is_valid_on_live_kernel(tc, bob, client):
    integrity = client.verify_audit_chain()
    assert integrity.status == "VALID"


def test_integrity_page_shows_valid_chain(tc, bob, client):
    body = bob.get("/audit/integrity").text
    assert "VALID" in body
    assert "first invalid event" not in body.lower()


def test_tampering_is_detected():
    kernel = build_demo_kernel()
    # tamper with the newest event after the chain has been written
    tampered = False
    for event in kernel.audit_events():
        event.context = dict(event.context, mutated="true")
        tampered = True
        break
    assert tampered
    client = GovernanceDashboardClient(kernel)
    integrity = client.verify_audit_chain()
    assert integrity.status == "BROKEN"
    assert integrity.first_invalid_event is not None


def test_integrity_page_reports_broken_chain():
    kernel = build_demo_kernel()
    for event in kernel.audit_events():
        event.event_hash = "deadbeef" * 4
        break
    app = create_app(GovernanceDashboardClient(kernel))
    tc = TestClient(app)
    tc.post("/login", data={"username": "bob", "password": "bob-pw"}, follow_redirects=True)
    body = tc.get("/audit/integrity").text
    assert "BROKEN" in body
    assert "deadbeef" in body


def test_reverify_post_requires_privileged_role(tc, login, csrf):
    login("bob")
    token = csrf("/audit/integrity")
    r = tc.post("/audit/integrity/verify", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 403


def test_reverify_post_succeeds_for_auditor(tc, login, csrf):
    login("alice")
    token = csrf("/audit/integrity")
    r = tc.post("/audit/integrity/verify", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 200
    assert "VALID" in r.text


def test_reverify_after_repair_returns_valid():
    """AC-2: repair (immutable chain → rebuild kernel) restores VALID."""
    kernel = build_demo_kernel()
    for event in kernel.audit_events():
        event.event_hash = "deadbeef" * 4
        break
    assert GovernanceDashboardClient(kernel).verify_audit_chain().status == "BROKEN"
    fresh = build_demo_kernel()
    assert GovernanceDashboardClient(fresh).verify_audit_chain().status == "VALID"


def test_fail_closed_when_kernel_unavailable():
    app = create_app(GovernanceDashboardClient(None))
    tc = TestClient(app)
    tc.post("/login", data={"username": "bob", "password": "bob-pw"}, follow_redirects=True)
    r = tc.get("/audit/integrity")
    assert r.status_code == 503
