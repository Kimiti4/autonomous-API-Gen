"""Authentication state machine — tracks where the principal is in the auth flow.

Privileged operations (capability grants, GitHub publication, etc.) are only
permitted from a fully-authenticated state.  Intermediate states never grant
privilege — this is the anti-vacuity mechanism for identity certification.
"""
from __future__ import annotations
from enum import Enum


class AuthState(str, Enum):
    UNAUTHENTICATED = "unauthenticated"
    PRIMARY_AUTHENTICATED = "primary_authenticated"
    MFA_REQUIRED = "mfa_required"
    MFA_VERIFIED = "mfa_verified"
    FULLY_AUTHENTICATED = "fully_authenticated"
    FAILED = "failed"


_PRIVILEGED_STATES: frozenset[AuthState] = frozenset({
    AuthState.FULLY_AUTHENTICATED,
})


def permits_privileged(state: AuthState) -> bool:
    """Return True only if the state grants access to privileged operations.

    PRIMARY_AUTHENTICATED, MFA_REQUIRED, and MFA_VERIFIED are all
    intermediate — they MUST NOT permit privileged access.
    """
    return state in _PRIVILEGED_STATES


def advance(state: AuthState, event: str) -> AuthState:
    """Deterministic state transitions.  Unknown events → FAILED."""
    transitions: dict[tuple[AuthState, str], AuthState] = {
        (AuthState.UNAUTHENTICATED, "primary_ok"): AuthState.PRIMARY_AUTHENTICATED,
        (AuthState.UNAUTHENTICATED, "primary_fail"): AuthState.FAILED,
        (AuthState.PRIMARY_AUTHENTICATED, "mfa_required"): AuthState.MFA_REQUIRED,
        (AuthState.PRIMARY_AUTHENTICATED, "mfa_not_required"): AuthState.FULLY_AUTHENTICATED,
        (AuthState.MFA_REQUIRED, "mfa_ok"): AuthState.MFA_VERIFIED,
        (AuthState.MFA_REQUIRED, "mfa_fail"): AuthState.FAILED,
        (AuthState.MFA_VERIFIED, "step_up_complete"): AuthState.FULLY_AUTHENTICATED,
    }
    return transitions.get((state, event), AuthState.FAILED)
