"""Identity gates I0-I9 — authentication, MFA, authorization, evidence, recovery."""

from __future__ import annotations

import asyncio
import pytest

from identity.composition import build_identity_stack
from identity.auth.totp import totp_code, generate_secret_b32
from identity.auth.recovery import hash_code
from identity.capabilities.grants import Capability, CapabilityGrant
from identity.evidence.action_recorder import project_action_to_v11_evidence


def run(c):
    return asyncio.run(c)


# ---------------------------------------------------------------------------
# I1 — email register + login
# ---------------------------------------------------------------------------

def test_i1_email_register_login():
    st = build_identity_stack()
    run(st.auth.register("x@y.z", "pw12345"))
    out = run(st.auth.login("x@y.z", "pw12345"))
    assert out.kind == "session"
    bad = run(st.auth.login("x@y.z", "wrong"))
    assert bad.kind == "failed"


def test_i1_duplicate_register():
    st = build_identity_stack()
    run(st.auth.register("a@b.c", "pw12345"))
    run(st.auth.register("a@b.c", "pw12345"))
    out = run(st.auth.login("a@b.c", "pw12345"))
    assert out.kind == "session"


# ---------------------------------------------------------------------------
# I3 — MFA step-up cycle
# ---------------------------------------------------------------------------

def test_i3_mfa_stepup_cycle():
    st = build_identity_stack()
    run(st.auth.register("m@y.z", "pw12345"))
    u = run(st.users.get_by_email("m@y.z"))
    kit = run(st.auth._mfa.enroll(u.principal))
    assert run(st.auth._mfa.confirm_and_activate(
        u.principal,
        kit.challenge.challenge_id,
        totp_code(kit.secret_b32),
        [hash_code(c) for c in kit.recovery_codes],
    ))
    out = run(st.auth.login("m@y.z", "pw12345"))
    assert out.kind == "mfa_required"
    done = run(st.auth.complete_mfa(
        out.principal,
        out.mfa_challenge.challenge_id,
        totp_code(kit.secret_b32),
    ))
    assert done.kind == "session"


# ---------------------------------------------------------------------------
# I4 — least privilege
# ---------------------------------------------------------------------------

def test_i4_least_privilege():
    g = CapabilityGrant(
        grant_id="g1", principal_id="p1",
        capability=Capability.GITHUB_REPOSITORY_CREATE,
        scope="repo:Kimiti4/*", granted_at="",
    )
    st = build_identity_stack([g])
    d, _ = run(st.authz.authorize_and_record(
        "p1", Capability.GITHUB_REPOSITORY_CREATE, "repo:Kimiti4/x"
    ))
    assert d.authorized
    d2, _ = run(st.authz.authorize_and_record(
        "p2", Capability.GITHUB_REPOSITORY_CREATE, "repo:Kimiti4/x"
    ))
    assert not d2.authorized


def test_i4_scope_exact_match():
    g = CapabilityGrant(
        grant_id="g2", principal_id="p1",
        capability=Capability.ISR_WRITE, scope="repo:single", granted_at="",
    )
    st = build_identity_stack([g])
    d, _ = run(st.authz.authorize_and_record("p1", Capability.ISR_WRITE, "repo:single"))
    assert d.authorized
    d2, _ = run(st.authz.authorize_and_record("p1", Capability.ISR_WRITE, "repo:other"))
    assert not d2.authorized


# ---------------------------------------------------------------------------
# I5 — action → v1.1 evidence
# ---------------------------------------------------------------------------

def test_i5_action_to_v11_evidence():
    st = build_identity_stack()
    _, rec = run(st.authz.authorize_and_record(
        "p1", Capability.DEPLOYMENT_EXECUTE, intent="deploy"
    ))
    ev = project_action_to_v11_evidence(rec)
    assert ev.evidenceType == "autonomous-action"
    assert len(ev.contentHash) == 64


# ---------------------------------------------------------------------------
# I6 — session rotation + revocation
# ---------------------------------------------------------------------------

def test_i6_session_rotation_revocation():
    st = build_identity_stack()
    run(st.auth.register("s@y.z", "pw12345"))
    out = run(st.auth.login("s@y.z", "pw12345"))
    old_id = out.session.session_id
    new = run(st.auth.rotate(old_id))
    assert run(st.auth._sessions.validate(old_id)) is None
    assert run(st.auth._sessions.validate(new.session_id)) is not None
    run(st.auth.logout(new.session_id))
    assert run(st.auth._sessions.validate(new.session_id)) is None


# ---------------------------------------------------------------------------
# I8 — password hashing security
# ---------------------------------------------------------------------------

def test_i8_password_hashing_secure():
    from identity.auth.password import PBKDF2PasswordHasher
    h = PBKDF2PasswordHasher()
    hashed = h.hash("secret")
    assert hashed != "secret"
    assert h.verify("secret", hashed)
    assert not h.verify("nope", hashed)


# ---------------------------------------------------------------------------
# I9 — recovery codes single-use
# ---------------------------------------------------------------------------

def test_i9_recovery_codes_single_use():
    st = build_identity_stack()
    run(st.auth.register("r@y.z", "pw12345"))
    u = run(st.users.get_by_email("r@y.z"))
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
