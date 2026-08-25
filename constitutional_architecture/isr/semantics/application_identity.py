"""44.1 Carrier -- part of generated system's semantic identity."""
from dataclasses import dataclass
@dataclass(frozen=True)
class ApplicationIdentity:
    identity_id: str; product_name: str; application_name: str; codename: str|None; description: str; repository_name: str; package_name: str; cli_name: str|None; domain_candidates: tuple[str,...]; naming_rationale: tuple[str,...]; intent_refs: tuple[str,...]; architecture_refs: tuple[str,...]
    def content_hash(self):
        from tiannara.domain.services.canonical import canonical_hash
        return canonical_hash(self.product_name)
