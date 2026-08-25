"""38.0 Organization Contract -- roles, authority, auditability."""
ROLES=("CEO","PM","Architect","Security","QA","DevOps")
def can_act(role: str, action: str) -> bool: return role in ROLES
