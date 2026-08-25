"""36.2 Authorization -- RBAC/ABAC/tenant isolation."""
from dataclasses import dataclass
@dataclass(frozen=True)
class AuthzCheck:
    subject: str; resource: str; allowed: bool
def check_isolation(tenant_a: str, tenant_b: str, resource_tenant: str) -> bool:
    return resource_tenant == tenant_a and resource_tenant != tenant_b
