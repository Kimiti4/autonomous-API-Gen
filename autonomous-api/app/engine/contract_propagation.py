"""Contract propagation across frontend/backend/data compiler artifacts."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ContractLink:
    contract_id: str
    producer_id: str
    consumer_id: str
    contract_kind: str
    compatibility: str = "unknown"  # compatible, breaking, unknown


@dataclass(frozen=True)
class PropagationFinding:
    contract_id: str
    artifact_id: str
    direction: str
    impact: str
    reason: str


@dataclass(frozen=True)
class PropagationReport:
    findings: tuple[PropagationFinding, ...]


def propagate_contract_change(
    contract: ContractLink,
    changed_contract: bool = True,
) -> PropagationReport:
    if not changed_contract:
        return PropagationReport(())
    findings = [
        PropagationFinding(
            contract.contract_id, contract.producer_id, "upstream",
            "review",
            "producer must satisfy the changed contract",
        ),
        PropagationFinding(
            contract.contract_id, contract.consumer_id, "downstream",
            "review",
            "consumer may depend on changed contract semantics",
        ),
    ]
    if contract.compatibility == "breaking":
        findings.extend((
            PropagationFinding(
                contract.contract_id, contract.consumer_id, "downstream",
                "migration-required",
                "breaking contract requires consumer migration or compatibility layer",
            ),
            PropagationFinding(
                contract.contract_id, contract.producer_id, "upstream",
                "verification-required",
                "producer behavior must be reverified against the new contract",
            ),
        ))
    elif contract.compatibility == "unknown":
        findings.append(PropagationFinding(
            contract.contract_id, contract.consumer_id, "downstream",
            "uncertainty",
            "compatibility has not been established",
        ))
    return PropagationReport(tuple(findings))


def affected_by_contracts(
    contracts: tuple[ContractLink, ...],
    changed_ids: tuple[str, ...],
) -> PropagationReport:
    changed = set(changed_ids)
    findings: list[PropagationFinding] = []
    for c in contracts:
        if c.contract_id in changed:
            findings.extend(propagate_contract_change(c).findings)
    return PropagationReport(tuple(findings))


def requires_compatibility_gate(report: PropagationReport) -> bool:
    return any(
        f.impact in {"migration-required", "uncertainty"}
        for f in report.findings
    )
