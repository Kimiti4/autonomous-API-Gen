"""Evolutionary feedback hook -- failures become the next generation."""
from __future__ import annotations

from dataclasses import dataclass

from tiannara.application.campaign.phase31_contract import build_phase31_contract, register_contract
from tiannara.application.evolution.ledger import EvolutionLedger


@dataclass(frozen=True)
class FailureDiagnosis:
    failing_cells: tuple[str, ...]
    root_causes: tuple[str, ...]


@dataclass(frozen=True)
class ISRMutation:
    target: str
    change: str


class EvolutionaryFeedbackHook:
    def diagnose(self, verdict, cell_results) -> FailureDiagnosis:
        failing = tuple(c.cell_id for c in cell_results if not c.success)
        causes = tuple("quality" for _ in failing[:1])
        return FailureDiagnosis(failing, causes)

    def propose_mutations(self, diagnosis: FailureDiagnosis) -> tuple[ISRMutation, ...]:
        return tuple(ISRMutation(target=cell, change="refine") for cell in diagnosis.failing_cells[:1])

    def prepare_campaign_c(self, mutations: tuple[ISRMutation, ...]) -> object:
        # New contract with new hash, never revision
        contract = build_phase31_contract(contract_id="phase31-contract-003")
        # Mutations operate on ISR carriers, never on contract
        return contract
