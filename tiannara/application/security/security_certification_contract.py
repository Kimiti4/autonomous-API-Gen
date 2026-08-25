"""33.0 Security Certification Contract -- frozen, hash-bound, ledger-anchored."""
from __future__ import annotations

from dataclasses import dataclass

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash

CONTRACT_ID = "security-contract-001"
CONTRACT_VERSION = "1.0.0"

SECURITY_DIMENSIONS = (
    "authentication",
    "authorization",
    "session_security",
    "input_validation",
    "output_encoding",
    "injection_resistance",
    "api_security",
    "cryptographic_correctness",
    "secrets_management",
    "dependency_supply_chain_security",
    "network_security",
    "data_protection",
    "concurrency_race_safety",
    "abuse_resistance",
    "business_logic_security",
    "runtime_container_isolation",
    "observability_incident_evidence",
    "recovery_behavior",
)

ATTACK_FAMILIES = (
    "sql_injection",
    "xss",
    "ssrf",
    "csrf",
    "privilege_escalation",
    "broken_authentication",
    "jwt_manipulation",
    "header_poisoning",
    "race_condition",
    "mass_assignment",
    "prototype_pollution",
    "dependency_confusion",
    "supply_chain",
    "secret_leakage",
    "credential_abuse",
    "replay",
    "rate_limit_bypass",
    "business_logic_abuse",
    "api_fuzzing",
    "command_injection",
    "path_traversal",
    "remote_code_execution",
    "container_escape",
)

CRITICAL_VULNERABILITY_CLASSES = (
    "remote_code_execution",
    "privilege_escalation",
    "broken_authentication",
    "sql_injection",
    "secret_leakage",
)


@dataclass(frozen=True)
class SecurityCertificationContract:
    contract_id: str
    version: str
    security_dimensions: tuple[str, ...]
    attack_families: tuple[str, ...]
    required_evidence: tuple[str, ...]
    critical_vulnerability_classes: tuple[str, ...]
    false_negative_bound: float
    false_positive_bound: float
    coverage_requirement: float
    recovery_requirement: str
    environment_requirement: str
    baseline_requirement: str
    exit_threshold: float
    bounded_policy: str
    verdict_vocabulary: tuple[str, ...]
    content_hash: str


def contract_body(contract: SecurityCertificationContract) -> dict:
    return {
        "contract_id": contract.contract_id,
        "version": contract.version,
        "security_dimensions": list(contract.security_dimensions),
        "attack_families": list(contract.attack_families),
        "required_evidence": list(contract.required_evidence),
        "critical_vulnerability_classes": list(contract.critical_vulnerability_classes),
        "false_negative_bound": contract.false_negative_bound,
        "false_positive_bound": contract.false_positive_bound,
        "coverage_requirement": contract.coverage_requirement,
        "recovery_requirement": contract.recovery_requirement,
        "environment_requirement": contract.environment_requirement,
        "baseline_requirement": contract.baseline_requirement,
        "exit_threshold": contract.exit_threshold,
        "bounded_policy": contract.bounded_policy,
        "verdict_vocabulary": list(contract.verdict_vocabulary),
    }


def hash_canonical(obj) -> str:
    return canonical_hash(obj)


def build_security_contract(
    contract_id: str = CONTRACT_ID,
    version: str = CONTRACT_VERSION,
) -> SecurityCertificationContract:
    tmp = SecurityCertificationContract(
        contract_id=contract_id,
        version=version,
        security_dimensions=SECURITY_DIMENSIONS,
        attack_families=ATTACK_FAMILIES,
        required_evidence=("attack_surface", "attack_execution", "detection", "containment", "recovery", "analyzer_evidence", "blind_evaluation"),
        critical_vulnerability_classes=CRITICAL_VULNERABILITY_CLASSES,
        false_negative_bound=0.001,
        false_positive_bound=0.05,
        coverage_requirement="all_attack_families_and_surface_types",
        recovery_requirement="time_to_recover_measured",
        environment_requirement="isolated_sandbox_per_artifact",
        baseline_requirement="human_baselines_provenance_blind",
        exit_threshold=0.995,
        bounded_policy="BOUNDED_NEVER_CERTIFIED",
        verdict_vocabulary=("CERTIFIED", "BOUNDED", "QUALIFIED_PARTIAL", "NOT_CERTIFIED"),
        content_hash="",
    )
    h = hash_canonical(contract_body(tmp))
    return SecurityCertificationContract(
        contract_id=contract_id,
        version=version,
        security_dimensions=SECURITY_DIMENSIONS,
        attack_families=ATTACK_FAMILIES,
        required_evidence=tmp.required_evidence,
        critical_vulnerability_classes=CRITICAL_VULNERABILITY_CLASSES,
        false_negative_bound=tmp.false_negative_bound,
        false_positive_bound=tmp.false_positive_bound,
        coverage_requirement=tmp.coverage_requirement,
        recovery_requirement=tmp.recovery_requirement,
        environment_requirement=tmp.environment_requirement,
        baseline_requirement=tmp.baseline_requirement,
        exit_threshold=tmp.exit_threshold,
        bounded_policy=tmp.bounded_policy,
        verdict_vocabulary=tmp.verdict_vocabulary,
        content_hash=h,
    )


SECURITY_CONTRACT = build_security_contract()


def register_security_contract(contract: SecurityCertificationContract, ledger: EvolutionLedger) -> str:
    body = contract_body(contract)
    assert contract.content_hash == hash_canonical(body), "content_hash mismatch"
    ev = EvolutionEvent(
        event_id=f"security-contract-{contract.contract_id}",
        evolution_id=contract.contract_id,
        sequence=0,
        event_type=EventType.CERTIFICATION,
        subject_id=contract.contract_id,
        payload={"security_contract": body, "content_hash": contract.content_hash},
    )
    return ledger.append_event(ev, evolution_id=contract.contract_id)
