"""Held-out acceptance hooks for the ExpenseLedger second-spec trial.

Loaded by ``run_trial.load_trial_hooks`` when the trial directory contains
this file. The runner, isolation boundary, and evidence contract stay
identical to the first trial; only the acceptance flow and frontend smoke
are trial-specific. Nothing in here is visible to the generation workspace.
"""

from __future__ import annotations

import json

from run_trial import _http, _record_ac, _run_node_smoke

RESOURCE = "claims"
CONTAINER_RESOURCE = "claim_vendors"
CLAIM_PAYLOAD = {
    "title": "Client dinner",
    "notes": "quarterly review",
    "amount": 84.5,
    "category": "meals",
    "status": "draft",
    "expense_date": "2026-10-20T00:00:00",
}


def run_acceptance_flow(base: str, api_key: str) -> dict:
    acs: dict[str, dict] = {}

    status, body = _http("GET", f"{base}/health")
    _record_ac(
        acs, "AC-07", "GET /health", status, body,
        status == 200 and "ok" in body,
    )

    status, body = _http("GET", f"{base}/{RESOURCE}")
    _record_ac(
        acs, "AC-06", f"GET /{RESOURCE} without key", status, body,
        status == 401,
    )

    status, body = _http("POST", f"{base}/{RESOURCE}", CLAIM_PAYLOAD, api_key)
    created = json.loads(body) if body else {}
    claim_id = created.get("id")
    created_ok = (
        status == 201
        and bool(claim_id)
        and created.get("title") == CLAIM_PAYLOAD["title"]
        and created.get("amount") == 84.5
        and created.get("category") == "meals"
        and created.get("status") == "draft"
        and "2026-10-20" in json.dumps(created)
    )
    _record_ac(acs, "AC-01", f"POST /{RESOURCE}", status, body, created_ok)

    status, body = _http("GET", f"{base}/{RESOURCE}", key=api_key)
    listed = json.loads(body) if body else []
    list_ok = status == 200 and isinstance(listed, list) and any(
        entry.get("id") == claim_id for entry in listed
    )
    _record_ac(acs, "AC-02", f"GET /{RESOURCE}", status, body, list_ok)

    status, body = _http(
        "GET", f"{base}/{RESOURCE}/{claim_id}", key=api_key
    )
    fetched = json.loads(body) if body else {}
    get_ok = status == 200 and fetched.get("id") == claim_id and fetched == created
    _record_ac(acs, "AC-03", f"GET /{RESOURCE}/{{id}}", status, body, get_ok)

    approved_payload = dict(CLAIM_PAYLOAD, status="approved")
    status_approved, body_approved = _http(
        "PUT", f"{base}/{RESOURCE}/{claim_id}", approved_payload, api_key
    )
    rejected_payload = dict(CLAIM_PAYLOAD, status="rejected")
    status_rejected, body_rejected = _http(
        "PUT", f"{base}/{RESOURCE}/{claim_id}", rejected_payload, api_key
    )
    rejected = json.loads(body_rejected) if body_rejected else {}
    put_ok = (
        status_approved == 200
        and (json.loads(body_approved) if body_approved else {}).get("status")
        == "approved"
        and status_rejected == 200
        and rejected.get("status") == "rejected"
    )
    _record_ac(
        acs,
        "AC-04",
        f"PUT /{RESOURCE}/{{id}} approved then rejected",
        status_rejected,
        body_approved + body_rejected,
        put_ok,
    )

    status, body = _http(
        "GET", f"{base}/{RESOURCE}/{claim_id}", key=api_key
    )
    after = json.loads(body) if body else {}
    retained = (
        status == 200
        and after.get("amount") == 84.5
        and after.get("category") == "meals"
        and "2026-10-20" in json.dumps(after)
    )
    _record_ac(
        acs, "AC-09", f"GET /{RESOURCE}/{{id}} after updates", status, body,
        retained,
    )

    minimal = {
        "title": "Taxi fare",
        "amount": 12.25,
        "category": "travel",
        "status": "draft",
    }
    status, body = _http("POST", f"{base}/{RESOURCE}", minimal, api_key)
    minimal_created = json.loads(body) if body else {}
    minimal_id = minimal_created.get("id")
    status2, body2 = _http(
        "GET", f"{base}/{RESOURCE}/{minimal_id}", key=api_key
    )
    minimal_fetched = json.loads(body2) if body2 else {}
    minimal_ok = (
        status == 201
        and status2 == 200
        and minimal_fetched.get("expense_date") in (None, "")
        and minimal_fetched.get("notes") in (None, "")
    )
    _record_ac(
        acs,
        "AC-10",
        f"POST /{RESOURCE} without expense date then GET",
        status2,
        body + body2,
        minimal_ok,
    )

    status, body = _http(
        "POST", f"{base}/{CONTAINER_RESOURCE}", {"name": "Acme Supplies"},
        api_key,
    )
    vendor = json.loads(body) if body else {}
    vendor_id = vendor.get("id")
    in_vendor_payload = dict(
        CLAIM_PAYLOAD, title="Office chairs", vendor_id=vendor_id
    )
    status3, body3 = _http(
        "POST", f"{base}/{RESOURCE}", in_vendor_payload, api_key
    )
    in_vendor = json.loads(body3) if body3 else {}
    in_vendor_id = in_vendor.get("id")
    status4, body4 = _http(
        "GET", f"{base}/{RESOURCE}/{in_vendor_id}", key=api_key
    )
    fetched_in_vendor = json.loads(body4) if body4 else {}
    status5, body5 = _http(
        "GET", f"{base}/{CONTAINER_RESOURCE}", key=api_key
    )
    vendors = json.loads(body5) if body5 else []
    membership_ok = (
        status == 201
        and bool(vendor_id)
        and status3 == 201
        and status4 == 200
        and fetched_in_vendor.get("vendor_id") == vendor_id
        and status5 == 200
        and any(entry.get("id") == vendor_id for entry in vendors)
    )
    _record_ac(
        acs,
        "AC-08",
        "POST /claim_vendors + claim with vendor_id + membership fetch",
        status5,
        body + body3 + body4 + body5,
        membership_ok,
    )

    status, body = _http("DELETE", f"{base}/{RESOURCE}/{claim_id}", key=api_key)
    status_after, body_after = _http(
        "GET", f"{base}/{RESOURCE}/{claim_id}", key=api_key
    )
    delete_ok = status == 204 and status_after == 404
    _record_ac(
        acs,
        "AC-05",
        f"DELETE /{RESOURCE}/{{id}} then GET",
        status_after,
        body + body_after,
        delete_ok,
    )

    return acs


def run_node_smoke(repo_root, slug: str, base: str, api_key: str) -> dict:
    payload = {
        "title": "Smoke claim",
        "status": "draft",
        "category": "supplies",
        "amount": 5.0,
        "notes": "from smoke",
    }
    return _run_node_smoke(
        repo_root,
        slug,
        base,
        api_key,
        RESOURCE,
        payload,
        {"status": "approved"},
    )
