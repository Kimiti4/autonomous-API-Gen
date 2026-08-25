"""Identity composition root — reference wiring of all identity services."""
from __future__ import annotations
from identity.auth.password import PBKDF2PasswordHasher
from identity.auth.email_authenticator import ReferenceEmailAuthenticator
from identity.auth.mfa_authenticator import ReferenceMfaAuthenticator
from identity.auth.session_manager import ReferenceSessionManager
from identity.auth.service import AuthenticationService
from identity.capabilities.grants import AuthorizationPort, CapabilityGrant, ReferenceAuthorizationPort
from identity.capabilities.authorization import AuthorizationService
from identity.stores.memory import InMemoryUserStore, InMemorySessionStore


class IdentityStack:
    def __init__(self, auth: AuthenticationService, authz: AuthorizationService, users: InMemoryUserStore) -> None:
        self.auth = auth
        self.authz = authz
        self.users = users


def build_identity_stack(grants: list[CapabilityGrant] | None = None) -> IdentityStack:
    users = InMemoryUserStore()
    sessions = InMemorySessionStore()
    email_auth = ReferenceEmailAuthenticator(users, PBKDF2PasswordHasher())
    mfa_auth = ReferenceMfaAuthenticator(users)
    session_mgr = ReferenceSessionManager(sessions)
    auth = AuthenticationService(email_auth, mfa_auth, session_mgr)
    authz = AuthorizationService(ReferenceAuthorizationPort(grants or []))
    return IdentityStack(auth, authz, users)
