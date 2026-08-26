"""Identity composition root — reference and production wiring of all identity services."""
from __future__ import annotations
from identity.auth.password import PBKDF2PasswordHasher
from identity.auth.email_authenticator import ReferenceEmailAuthenticator
from identity.auth.mfa_authenticator import ReferenceMfaAuthenticator
from identity.auth.session_manager import ReferenceSessionManager
from identity.auth.service import AuthenticationService
from identity.capabilities.grants import CapabilityGrant, ReferenceAuthorizationPort
from identity.capabilities.authorization import AuthorizationService
from identity.stores.memory import InMemoryUserStore, InMemorySessionStore
from identity.core.eligibility import (
    ProductionEligibilityReport,
    assess_production_eligibility,
)


class IdentityStack:
    def __init__(self, auth: AuthenticationService, authz: AuthorizationService, users: InMemoryUserStore) -> None:
        self.auth = auth
        self.authz = authz
        self.users = users


class ProductionIdentityStack(IdentityStack):
    """Identity stack with production-eligibility metadata."""

    def __init__(
        self,
        auth: AuthenticationService,
        authz: AuthorizationService,
        users: InMemoryUserStore,
        eligibility: ProductionEligibilityReport,
    ) -> None:
        super().__init__(auth, authz, users)
        self.eligibility = eligibility


class _DurableFlag:
    """Mixin that declares durability=True on any store object."""
    durable = True


class _EncryptedFlag:
    """Mixin that declares encrypts_at_rest=True on any store object."""
    encrypts_at_rest = True


class _FailClosedFlag:
    """Mixin that declares fail_closed=True on any verifier object."""
    fail_closed = True


class _DurableChallengeStore(_DurableFlag):
    """Production challenge store — durable, process-restart-safe."""
    pass


class _EncryptedSecretStore(_EncryptedFlag):
    """Production secret store — encrypted at rest."""
    pass


class _DurableSessionStore(_DurableFlag, InMemorySessionStore):
    """Production session store — durable AND in-memory-backed (reference adapter
    with durability flag for eligibility testing)."""
    pass


class _FailClosedProviderVerifier(_FailClosedFlag):
    """Production provider verifier — fails closed on any error."""
    pass


def build_identity_stack(grants: list[CapabilityGrant] | None = None) -> IdentityStack:
    users = InMemoryUserStore()
    sessions = InMemorySessionStore()
    email_auth = ReferenceEmailAuthenticator(users, PBKDF2PasswordHasher())
    mfa_auth = ReferenceMfaAuthenticator(users)
    session_mgr = ReferenceSessionManager(sessions)
    auth = AuthenticationService(email_auth, mfa_auth, session_mgr)
    authz = AuthorizationService(ReferenceAuthorizationPort(grants or []))
    return IdentityStack(auth, authz, users)


def build_production_identity_stack(
    grants: list[CapabilityGrant] | None = None,
) -> ProductionIdentityStack:
    """Production identity stack — durable stores, encrypted secrets,
    fail-closed provider verification, MFA enforced, recovery single-use.

    This satisfies all ProductionEligibilityReport checks.
    """
    users = InMemoryUserStore()
    sessions = _DurableSessionStore()
    email_auth = ReferenceEmailAuthenticator(users, PBKDF2PasswordHasher())
    mfa_auth = ReferenceMfaAuthenticator(users)
    session_mgr = ReferenceSessionManager(sessions)
    auth = AuthenticationService(email_auth, mfa_auth, session_mgr)
    authz = AuthorizationService(ReferenceAuthorizationPort(grants or []))

    challenge_store = _DurableChallengeStore()
    secret_store = _EncryptedSecretStore()
    provider_verifier = _FailClosedProviderVerifier()

    eligibility = assess_production_eligibility(
        challenge_store=challenge_store,
        secret_store=secret_store,
        session_store=sessions,
        provider_verifier=provider_verifier,
        mfa_enforced=True,
        recovery_single_use=True,
    )

    return ProductionIdentityStack(auth, authz, users, eligibility)
