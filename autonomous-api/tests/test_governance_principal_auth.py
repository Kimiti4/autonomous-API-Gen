import asyncio
import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.governance_routes import (
    _require_governance_actor,
    _verify_council_attestations,
)
from app.core.governance.commands import RequestGovernanceDecision
from app.middleware.security import (
    AuthContext,
    PrincipalApiKeyAuthProvider,
)


COUNCIL_KEYS = {
    "council-1": "member-one-secret",
    "council-2": "member-two-secret",
}


def _request_with_header(name, value):
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(name.lower().encode(), value.encode())],
    })


def _decision(signatures=None):
    return RequestGovernanceDecision(
        candidateId="candidate-42",
        generation=7,
        fromState="selected",
        toState="deployed",
        requestedBy="council-1",
        decidedBy=["council-1", "council-2"],
        verdict="approve",
        authorizesTransition=True,
        rationale="independently reviewed artifact",
        evidenceRefs=["sha256:" + ("a" * 64)],
        memberSignatures=signatures or {},
    )


def _sign(command, keys):
    payload = command.model_dump(mode="json", exclude={"memberSignatures"})
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return {
        member: hmac.new(secret.encode(), canonical, hashlib.sha256).hexdigest()
        for member, secret in keys.items()
    }


def test_principal_api_key_provider_returns_only_its_bound_scope():
    provider = PrincipalApiKeyAuthProvider(
        keys=COUNCIL_KEYS,
        header_name="X-Governance-Council-Key",
        scope="governance:decide",
    )

    auth = asyncio.run(
        provider.authenticate(
            _request_with_header("X-Governance-Council-Key", COUNCIL_KEYS["council-1"])
        )
    )
    assert auth == AuthContext(
        subject="council-1",
        scopes=("governance:decide",),
    )

    assert asyncio.run(
        provider.authenticate(
            _request_with_header("X-Governance-Council-Key", "wrong-secret")
        )
    ) is None


def test_council_decision_requires_valid_attestation_from_each_named_member(monkeypatch):
    command = _decision()
    signed = command.model_copy(update={"memberSignatures": _sign(command, COUNCIL_KEYS)})
    monkeypatch.setattr(
        "app.api.governance_routes.get_settings",
        lambda: SimpleNamespace(GOVERNANCE_COUNCIL_API_KEYS=COUNCIL_KEYS),
    )

    _verify_council_attestations(
        signed,
        AuthContext(subject="council-1", scopes=("governance:decide",)),
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda signatures: signatures.pop("council-2"),
        lambda signatures: signatures.update({"council-2": "0" * 64}),
    ],
)
def test_council_decision_rejects_missing_or_invalid_member_signature(monkeypatch, mutate):
    command = _decision()
    signatures = _sign(command, COUNCIL_KEYS)
    mutate(signatures)
    signed = command.model_copy(update={"memberSignatures": signatures})
    monkeypatch.setattr(
        "app.api.governance_routes.get_settings",
        lambda: SimpleNamespace(GOVERNANCE_COUNCIL_API_KEYS=COUNCIL_KEYS),
    )

    with pytest.raises(HTTPException) as error:
        _verify_council_attestations(
            signed,
            AuthContext(subject="council-1", scopes=("governance:decide",)),
        )
    assert error.value.status_code == 403


def test_council_decision_rejects_authenticated_actor_spoofing(monkeypatch):
    command = _decision()
    signed = command.model_copy(update={"memberSignatures": _sign(command, COUNCIL_KEYS)})
    monkeypatch.setattr(
        "app.api.governance_routes.get_settings",
        lambda: SimpleNamespace(GOVERNANCE_COUNCIL_API_KEYS=COUNCIL_KEYS),
    )

    with pytest.raises(HTTPException) as error:
        _verify_council_attestations(
            signed,
            AuthContext(subject="admin", scopes=("control",)),
        )
    assert error.value.status_code == 403


def test_council_decision_rejects_payload_tampering_after_signing(monkeypatch):
    command = _decision()
    signatures = _sign(command, COUNCIL_KEYS)
    tampered = command.model_copy(
        update={
            "rationale": "changed after member signatures",
            "memberSignatures": signatures,
        }
    )
    monkeypatch.setattr(
        "app.api.governance_routes.get_settings",
        lambda: SimpleNamespace(GOVERNANCE_COUNCIL_API_KEYS=COUNCIL_KEYS),
    )

    with pytest.raises(HTTPException, match="attestation is invalid"):
        _verify_council_attestations(
            tampered,
            AuthContext(subject="council-1", scopes=("governance:decide",)),
        )


def test_governance_actor_guard_rejects_wrong_scope_and_spoofed_certifier():
    with pytest.raises(HTTPException) as wrong_scope:
        _require_governance_actor(
            AuthContext(subject="admin", scopes=("control",)),
            scope="governance:certify",
            actor="admin",
        )
    assert wrong_scope.value.status_code == 403

    with pytest.raises(HTTPException) as spoofed_actor:
        _require_governance_actor(
            AuthContext(subject="admin", scopes=("governance:certify",)),
            scope="governance:certify",
            actor="certifier-1",
        )
    assert spoofed_actor.value.status_code == 403
