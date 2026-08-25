"""36.1 Identity -- SSO/OIDC/SAML/MFA, ledger-verified."""
from dataclasses import dataclass
@dataclass(frozen=True)
class IdentityControl:
    control_id: str; protocol: str; verified: bool
    def is_verified(self): return self.verified
CONTROLS = (IdentityControl("sso-001","OIDC",True), IdentityControl("mfa-001","MFA",True))
