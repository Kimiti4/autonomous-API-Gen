"""
Phase 28 — Milestone 5A spec §15.4.3: approval workflow tests (task 5A.3).

Approving/rejecting through the BFF records the decision on the kernel,
is audit-visible, respects permissions/CSRF, and is reflected in the queue.
"""

from __future__ import annotations


def test_pending_approval_visible_in_queue(tc, login, client, pending_approval):
    login("carol")
    body = tc.get("/approvals").text
    assert pending_approval in body


def test_approve_through_bff_records_decision(tc, login, csrf, client, pending_approval):
    login("carol")
    token = csrf(f"/approvals/{pending_approval}")
    r = tc.post(
        f"/approvals/{pending_approval}/approve",
        data={"comment": "approved", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    record = client.get_approval(pending_approval)
    assert record.status == "APPROVED"
    assert record.comments == "approved"


def test_reject_through_bff_records_decision(tc, login, csrf, client, kernel, pending_approval):
    login("carol")
    token = csrf(f"/approvals/{pending_approval}")
    r = tc.post(
        f"/approvals/{pending_approval}/reject",
        data={"comment": "missing simulation", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 303
    record = client.get_approval(pending_approval)
    assert record.status == "REJECTED"
    assert record.comments == "missing simulation"


def test_approval_decision_is_audit_visible(tc, login, csrf, client, kernel, pending_approval):
    login("carol")
    token = csrf(f"/approvals/{pending_approval}")
    tc.post(
        f"/approvals/{pending_approval}/approve",
        data={"comment": "audit me", "csrf_token": token},
        follow_redirects=False,
    )
    events = [
        e for e in client.list_audit_events()
        if e.event_type == "APPROVAL_DECIDED" and e.subject_id == pending_approval
    ]
    assert events, "approval decision must be recorded in the audit log"


def test_approval_detail_shows_decision_after_approve(tc, login, csrf, client, pending_approval):
    login("carol")
    token = csrf(f"/approvals/{pending_approval}")
    tc.post(
        f"/approvals/{pending_approval}/approve",
        data={"comment": "ok", "csrf_token": token},
        follow_redirects=False,
    )
    body = tc.get(f"/approvals/{pending_approval}").text
    assert "APPROVED" in body
    assert "ok" in body


def test_approving_twice_is_rejected(tc, login, csrf, client, kernel, pending_approval):
    login("carol")
    token = csrf(f"/approvals/{pending_approval}")
    tc.post(
        f"/approvals/{pending_approval}/approve",
        data={"comment": "first", "csrf_token": token},
        follow_redirects=False,
    )
    r = tc.post(
        f"/approvals/{pending_approval}/reject",
        data={"comment": "second", "csrf_token": token},
        follow_redirects=False,
    )
    assert r.status_code == 422
    assert client.get_approval(pending_approval).status == "APPROVED"


def test_queue_status_filter(tc, login, client, pending_approval):
    login("carol")
    body = tc.get("/approvals?status=PENDING").text
    assert pending_approval in body
    assert "No approvals." in tc.get("/approvals?status=EXPIRED").text
    assert tc.get("/approvals?status=BOGUS").status_code == 422


def test_approval_shows_required_approver(tc, login, client, pending_approval):
    login("carol")
    record = client.get_approval(pending_approval)
    body = tc.get(f"/approvals/{pending_approval}").text
    assert record.approver_id in body
