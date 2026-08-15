"""
Phase 28 — Milestone 5A spec §15.4.4: exception registry tests (task 5A.4).

Exceptions are listed with status filtering, revocable only by privileged
roles, and revocation is immediate + audit-visible.
"""

from __future__ import annotations


def test_exception_list_shows_demo_exception(tc, login, client, active_exception):
    login("bob")
    body = tc.get("/exceptions").text
    assert active_exception.id in body


def test_exception_status_filter(tc, login, client, active_exception):
    login("bob")
    body = tc.get("/exceptions?status=ACTIVE").text
    assert active_exception.id in body
    empty = tc.get("/exceptions?status=REVOKED").text
    assert active_exception.id not in empty


def test_exception_detail_shows_scope_and_justification(tc, login, client, active_exception):
    login("bob")
    detail = client.get_exception(active_exception.id)
    body = tc.get(f"/exceptions/{active_exception.id}").text
    assert detail.justification in body
    assert "ACTIVE" in body


def test_revoke_exception_is_immediate(tc, login, csrf, client, active_exception):
    login("alice")
    token = csrf(f"/exceptions/{active_exception.id}")
    r = tc.post(
        f"/exceptions/{active_exception.id}/revoke",
        data={"justification": "widget module shipped", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert client.get_exception(active_exception.id).status == "REVOKED"


def test_revoked_exception_disappears_from_active_list(tc, login, csrf, client, active_exception):
    login("alice")
    token = csrf(f"/exceptions/{active_exception.id}")
    tc.post(
        f"/exceptions/{active_exception.id}/revoke",
        data={"justification": "done", "csrf_token": token},
        follow_redirects=False,
    )
    body = tc.get("/exceptions?status=ACTIVE").text
    assert active_exception.id not in body


def test_revocation_is_audit_visible(tc, login, csrf, client, active_exception):
    login("alice")
    token = csrf(f"/exceptions/{active_exception.id}")
    tc.post(
        f"/exceptions/{active_exception.id}/revoke",
        data={"justification": "audited revocation", "csrf_token": token},
        follow_redirects=False,
    )
    events = [
        e for e in client.list_audit_events()
        if e.event_type in ("EXCEPTION_REVOKED", "EXCEPTION_REVOKE_AUDITED")
        and e.subject_id == active_exception.id
    ]
    assert events, "revocation must be recorded in the audit log"


def test_revoke_requires_privileged_role(tc, login, csrf, active_exception):
    login("bob")
    token = csrf(f"/exceptions/{active_exception.id}")
    r = tc.post(
        f"/exceptions/{active_exception.id}/revoke",
        data={"justification": "nope", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_revoke_unknown_exception_returns_404(tc, login, csrf, client):
    login("alice")
    token = csrf("/exceptions")
    r = tc.post(
        "/exceptions/does-not-exist/revoke",
        data={"justification": "j", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 404
