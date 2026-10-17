"""System-wide security posture as a first-class semantic ISR gene."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityPosture:
    authentication: str
    authorization: str
    data_classification: str
    encryption_in_transit_required: bool
    encryption_at_rest_required: bool
    audit_logging_required: bool
    secrets_management_required: bool

    def __post_init__(self) -> None:
        allowed_authentication = {
            "anonymous", "credential_based", "token_based",
            "federated_identity", "mutual_authentication",
        }
        allowed_authorization = {"none", "rbac", "abac", "policy_based"}
        allowed_classification = {"public", "internal", "confidential", "restricted"}
        if self.authentication not in allowed_authentication:
            raise ValueError("unsupported authentication posture")
        if self.authorization not in allowed_authorization:
            raise ValueError("unsupported authorization model")
        if self.data_classification not in allowed_classification:
            raise ValueError("unsupported data classification")
        for field_name in (
            "encryption_in_transit_required",
            "encryption_at_rest_required",
            "audit_logging_required",
            "secrets_management_required",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ValueError(f"{field_name} must be boolean")
