"""34.3 Security Policy Compiler -- ISR-derived obligations only, never code."""
from __future__ import annotations
from dataclasses import dataclass
from tiannara.domain.services.canonical import canonical_hash

POLICY_RULES = (
    {"rule_id": "SEC-SQL-001", "family": "sql_injection", "requires": "external_api+user_input", "evidence": "sql_injection_resistance"},
    {"rule_id": "SEC-AUTH-001", "family": "broken_authentication", "requires": "authentication_requirement", "evidence": "auth_resistance"},
    {"rule_id": "SEC-SECRET-001", "family": "secret_leakage", "requires": "secrets_management", "evidence": "secret_scan"},
)

@dataclass(frozen=True)
class SecurityObligation:
    obligation_id: str; source_refs: tuple[str,...]; rule_id: str; rule_version: str; attack_family: str; required_evidence: str

def _derive_id(source_refs, rule_id):
    return canonical_hash({"sources": sorted(source_refs), "rule": rule_id})[:12]

def compile_policy(isr_facts: dict) -> tuple[SecurityObligation, ...]:
    """isr_facts: dict fact_name -> source_refs list, e.g., {'external_api': ['isr:api-1'], 'user_input': ['isr:input-1']}"""
    obligations = []
    for rule in POLICY_RULES:
        req = rule["requires"]
        # Simple: if all tokens in req present in isr_facts keys
        tokens = [t.strip() for t in req.replace("+", " ").split()]
        if all(any(t in k for k in isr_facts) for t in tokens):
            # Collect source refs for those facts
            srcs = []
            for k, refs in isr_facts.items():
                if any(t in k for t in tokens):
                    srcs.extend(refs)
            if not srcs:
                continue
            obligations.append(SecurityObligation(
                obligation_id=f"sec-oblig-{_derive_id(tuple(srcs), rule['rule_id'])}",
                source_refs=tuple(sorted(set(srcs))),
                rule_id=rule["rule_id"],
                rule_version="1.0.0",
                attack_family=rule["family"],
                required_evidence=rule["evidence"],
            ))
    # Deterministic sorted
    return tuple(sorted(obligations, key=lambda o: o.obligation_id))

def validate_obligation(ob):
    if not ob.source_refs or not ob.rule_id:
        raise ValueError("provenance or rule missing")
