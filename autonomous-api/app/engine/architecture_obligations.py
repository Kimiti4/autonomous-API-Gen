"""CAP-002 architecture obligation and traceability model.

Turns ISR semantics into explicit architecture obligations. It does not select
an implementation technology and does not claim an obligation is satisfied
merely because words resemble one another.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .requirement_isr import EngineeringISR


@dataclass(frozen=True)
class ArchitectureObligation:
    obligation_id: str
    source_id: str
    obligation_type: str
    statement: str
    verification: tuple[str, ...] = ()
    required_properties: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "source_id": self.source_id,
            "obligation_type": self.obligation_type,
            "statement": self.statement,
            "verification": list(self.verification),
            "required_properties": list(self.required_properties),
        }


@dataclass(frozen=True)
class ObligationMapping:
    obligation_id: str
    component_ids: tuple[str, ...]
    satisfied: bool
    rationale: str
    evidence_requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__ | {
            "component_ids": list(self.component_ids),
            "evidence_requirements": list(self.evidence_requirements),
        }


def derive_architecture_obligations(isr: EngineeringISR) -> tuple[ArchitectureObligation, ...]:
    obligations: list[ArchitectureObligation] = []
    for invariant in isr.invariants:
        obligations.append(ArchitectureObligation(
            f"AO-{invariant.invariant_id}", invariant.invariant_id, "invariant",
            invariant.statement,
            (f"state-machine/replay verification for {invariant.invariant_id}",),
            ("preserve invariant across retries and failures",),
        ))
    for policy in isr.policies:
        obligations.append(ArchitectureObligation(
            f"AO-{policy.policy_id}", policy.policy_id, "policy",
            policy.statement,
            (f"authorization/control-path verification for {policy.policy_id}",),
            ("policy enforcement at the relevant trust boundary",),
        ))
    for interface in isr.interfaces:
        obligations.append(ArchitectureObligation(
            f"AO-{interface.interface_id}", interface.interface_id, "interface",
            interface.statement,
            (f"contract verification for {interface.interface_id}",),
            ("explicit input/output contract",),
        ))
    return tuple(obligations)


def map_obligations(
    obligations: tuple[ArchitectureObligation, ...],
    component_ids: tuple[str, ...],
    *,
    satisfied: bool,
    rationale: str,
) -> tuple[ObligationMapping, ...]:
    return tuple(ObligationMapping(
        o.obligation_id, component_ids, satisfied, rationale, o.verification
    ) for o in obligations)


def certify_architecture_mappings(
    obligations: tuple[ArchitectureObligation, ...],
    mappings: tuple[ObligationMapping, ...],
) -> tuple[str, ...]:
    expected = {o.obligation_id for o in obligations}
    actual = {m.obligation_id for m in mappings}
    findings: list[str] = []
    for missing in sorted(expected - actual):
        findings.append(f"missing obligation mapping: {missing}")
    for extra in sorted(actual - expected):
        findings.append(f"unknown obligation mapping: {extra}")
    for mapping in mappings:
        if not mapping.satisfied:
            findings.append(f"unsatisfied obligation: {mapping.obligation_id}")
        if not mapping.component_ids:
            findings.append(f"obligation has no component mapping: {mapping.obligation_id}")
        if not mapping.evidence_requirements:
            findings.append(f"obligation has no evidence requirement: {mapping.obligation_id}")
    return tuple(findings)
