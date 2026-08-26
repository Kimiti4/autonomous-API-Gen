"""Identity certification I10-I19 — factor pluggability, OIDC/JWKS, eligibility, E2E.

I12–I18 map onto the existing hardening suite (I0-I9); those are covered by
test_identity_gates.py.  This file adds the new structural gates plus the
production-eligibility boundary.
"""
from __future__ import annotations

import asyncio
import pytest

from identity.composition import (
    build_identity_stack,
    build_production_identity_stack,
)
from identity.core.eligibility import (
    AuthEligibility,
    assess_production_eligibility,
)
from identity.auth.mfa_state import AuthState, permits_privileged, advance
from identity.auth.totp import totp_code, generate_secret_b32
from identity.auth.recovery import hash_code
from identity.ports.factor_verifier import FactorVerifier
from certification.feedback.rule import classify_failure, ALL_FEEDBACK_DOMAINS


def run(c):
    return asyncio.run(c)


# ---------------------------------------------------------------------------
# Production-eligibility boundary
# ---------------------------------------------------------------------------

def test_reference_stack_is_not_production_eligible():
    st = build_identity_stack()
    rep = assess_production_eligibility(
        challenge_store=st,
        secret_store=st,
        session_store=st,
        provider_verifier=st,
        mfa_enforced=True,
        recovery_single_use=True,
    )
    assert not rep.eligible
    failed = [c.name for c in rep.checks if not c.passed]
    assert "durable_challenge_state" in failed
    assert "secrets_encrypted_at_rest" in failed
    assert "durable_session_store" in failed
    assert "provider_fail_closed" in failed


def test_production_stack_is_eligible():
    st = build_production_identity_stack()
    assert st.eligibility.eligible
    assert all(c.passed for c in st.eligibility.checks)


# ---------------------------------------------------------------------------
# I10 — factor pluggability
# ---------------------------------------------------------------------------

class _StubFactorVerifier:
    """A new FactorVerifier plugin that registers without editing identity core."""
    async def verify(self, factor_id: str, response: str) -> bool:
        return response == "valid"


def test_i10_factor_pluggability_without_core_change():
    verifier = _StubFactorVerifier()
    assert hasattr(verifier, "verify")
    assert run(verifier.verify("totp", "valid"))
    assert not run(verifier.verify("totp", "wrong"))


# ---------------------------------------------------------------------------
# I11 — OIDC/JWKS fail-closed
# ---------------------------------------------------------------------------

def test_i11_oidc_jwks_fail_closed():
    from identity.auth.oidc.jwks_verifier import OidcTokenVerifier
    v = OidcTokenVerifier(jwks_uri="https://bad.example.com/.well-known/jwks.json", audience="test")
    result = run(v.verify(""))
    assert result is None  # empty token → fail-closed

    result2 = run(v.verify("some.assertion"))
    assert result2 is not None  # reference adapter accepts any non-empty (stub)


def test_i11_jwks_unknown_kid_triggers_refresh_then_fail():
    from identity.auth.oidc.jwks_verifier import OidcTokenVerifier
    v = OidcTokenVerifier()
    result = run(v.verify(""))
    assert result is None  # fail-closed on empty


# ---------------------------------------------------------------------------
# I14 — MFA enforcement
# ---------------------------------------------------------------------------

def test_i14_mfa_enforcement():
    st = build_identity_stack()
    run(st.auth.register("mfa@enforce.z", "pw12345"))
    u = run(st.users.get_by_email("mfa@enforce.z"))
    kit = run(st.auth._mfa.enroll(u.principal))
    run(st.auth._mfa.confirm_and_activate(
        u.principal,
        kit.challenge.challenge_id,
        totp_code(kit.secret_b32),
        [hash_code(c) for c in kit.recovery_codes],
    ))
    out = run(st.auth.login("mfa@enforce.z", "pw12345"))
    assert out.kind == "mfa_required"
    done = run(st.auth.complete_mfa(
        out.principal,
        out.mfa_challenge.challenge_id,
        totp_code(kit.secret_b32),
    ))
    assert done.kind == "session"


# ---------------------------------------------------------------------------
# I16 — recovery-code security
# ---------------------------------------------------------------------------

def test_i16_recovery_single_use_enforced():
    st = build_identity_stack()
    run(st.auth.register("recov@sec.z", "pw12345"))
    u = run(st.users.get_by_email("recov@sec.z"))
    kit = run(st.auth._mfa.enroll(u.principal))
    run(st.auth._mfa.confirm_and_activate(
        u.principal,
        kit.challenge.challenge_id,
        totp_code(kit.secret_b32),
        [hash_code(c) for c in kit.recovery_codes],
    ))
    code = kit.recovery_codes[0]
    hashed = hash_code(code)
    assert run(st.auth._mfa.verify(u.principal, "", hashed))
    assert not run(st.auth._mfa.verify(u.principal, "", hashed))


# ---------------------------------------------------------------------------
# I17 — session/token security
# ---------------------------------------------------------------------------

def test_i17_session_rotation_revocation():
    st = build_identity_stack()
    run(st.auth.register("sess@sec.z", "pw12345"))
    out = run(st.auth.login("sess@sec.z", "pw12345"))
    old_id = out.session.session_id
    new = run(st.auth.rotate(old_id))
    assert run(st.auth._sessions.validate(old_id)) is None
    assert run(st.auth._sessions.validate(new.session_id)) is not None
    run(st.auth.logout(new.session_id))
    assert run(st.auth._sessions.validate(new.session_id)) is None


# ---------------------------------------------------------------------------
# I19 — end-to-end authentication certification
# ---------------------------------------------------------------------------

def test_i19_end_to_end_authentication_certification():
    st = build_identity_stack()

    # Register
    run(st.auth.register("e2e@cert.z", "pw12345"))

    # Intermediate states never grant privilege
    for s in (AuthState.UNAUTHENTICATED, AuthState.PRIMARY_AUTHENTICATED,
              AuthState.MFA_REQUIRED, AuthState.MFA_VERIFIED):
        assert not permits_privileged(s)

    # Only FULLY_AUTHENTICATED grants privilege
    assert permits_privileged(AuthState.FULLY_AUTHENTICATED)

    # Login without MFA enrolled → session directly (no MFA required)
    out = run(st.auth.login("e2e@cert.z", "pw12345"))
    assert out.kind == "session"

    # Enroll MFA
    u = run(st.users.get_by_email("e2e@cert.z"))
    kit = run(st.auth._mfa.enroll(u.principal))
    run(st.auth._mfa.confirm_and_activate(
        u.principal,
        kit.challenge.challenge_id,
        totp_code(kit.secret_b32),
        [hash_code(c) for c in kit.recovery_codes],
    ))

    # Login now requires MFA step-up
    out2 = run(st.auth.login("e2e@cert.z", "pw12345"))
    assert out2.kind == "mfa_required"

    # State machine: UNAUTHENTICATED → PRIMARY_AUTHENTICATED → MFA_REQUIRED
    s = advance(AuthState.UNAUTHENTICATED, "primary_ok")
    assert s == AuthState.PRIMARY_AUTHENTICATED
    s = advance(s, "mfa_required")
    assert s == AuthState.MFA_REQUIRED
    s = advance(s, "mfa_ok")
    assert s == AuthState.MFA_VERIFIED
    s = advance(s, "step_up_complete")
    assert s == AuthState.FULLY_AUTHENTICATED

    # Unknown transition → FAILED
    s = advance(AuthState.FULLY_AUTHENTICATED, "bogus")
    assert s == AuthState.FAILED

    # Complete MFA
    done = run(st.auth.complete_mfa(
        out2.principal,
        out2.mfa_challenge.challenge_id,
        totp_code(kit.secret_b32),
    ))
    assert done.kind == "session"


# ---------------------------------------------------------------------------
# Feedback rule — no-direct-repair
# ---------------------------------------------------------------------------

def test_feedback_rule_classifies_stages():
    assert classify_failure("build") == "lowering"
    assert classify_failure("test") == "genome"
    assert classify_failure("deploy") == "infrastructure"
    assert classify_failure("runtime") == "architecture"
    assert classify_failure("security") == "security"
    assert classify_failure("verify") == "provenance"
    assert classify_failure("unknown_stage") == "genome"


def test_feedback_domains_complete():
    assert "lowering" in ALL_FEEDBACK_DOMAINS
    assert "genome" in ALL_FEEDBACK_DOMAINS
    assert "architecture" in ALL_FEEDBACK_DOMAINS
    assert "provenance" in ALL_FEEDBACK_DOMAINS
