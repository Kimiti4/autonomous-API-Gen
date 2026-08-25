"""Contract-002 -- same law, complete evidence."""
from __future__ import annotations

from tiannara.application.campaign.phase31_contract import (
    CHALLENGE_CATEGORIES,
    VARIATION_AXES,
    CampaignPopulation,
    CertificationAccuracyBounds,
    Phase31CertificationContract,
    PreRegistrationInvariant,
    PROBES,
    SUCCESS_DEFINITION,
    EXIT_GATE,
    StatisticalRequirements,
    AnalyzerProvisioningScope,
    contract_body,
    hash_canonical,
    register_contract,
)
from tiannara.application.campaign.provisioning import ProvisioningAcceptanceGate


def build_contract_002(provisioning_event_ref: str | None = None) -> Phase31CertificationContract:
    population = CampaignPopulation(
        categories=CHALLENGE_CATEGORIES,
        variation_axes=VARIATION_AXES,
        minimum_per_category=80,
        total_generations=80 * len(CHALLENGE_CATEGORIES),
        stratification_rule="stratified coverage across all categories and all variation axes",
    )
    accuracy_bounds = CertificationAccuracyBounds(max_false_acceptance_rate=0.001, max_false_rejection_rate=0.02)
    analyzer_scope = AnalyzerProvisioningScope(
        required_tools=ProvisioningAcceptanceGate.REQUIRED_TOOLS,
        provisioning_state="PROVISIONED",
        bounded_coverage=(),
        provisioning_gate_ref=provisioning_event_ref,
    )
    statistical_requirements = StatisticalRequirements(
        stratification_required=True,
        minimum_per_category=80,
        distinguishability="n sufficient to separate 99.5% from 99% at 95% confidence",
        adversarial_accounting_separate=True,
    )
    pre_registration = PreRegistrationInvariant(frozen_before_campaign=True, hash_bound=True, ledger_anchored=True)
    declared_assumptions = ("all 11 analyzers CERTIFICATION_ELIGIBLE before campaign start", "failures are expected and exercised, not avoided")
    tmp = Phase31CertificationContract(
        contract_id="phase31-contract-002",
        campaign_purpose="Compiler correctness under fully-evidenced Phase 32 certification",
        population=population,
        success_definition=SUCCESS_DEFINITION,
        exit_gate=EXIT_GATE,
        accuracy_bounds=accuracy_bounds,
        probe_populations=PROBES,
        analyzer_scope=analyzer_scope,
        statistical_requirements=statistical_requirements,
        pre_registration=pre_registration,
        declared_assumptions=declared_assumptions,
        content_hash="",
    )
    body = contract_body(tmp)
    content_hash = hash_canonical(body)
    return Phase31CertificationContract(
        contract_id=tmp.contract_id,
        campaign_purpose=tmp.campaign_purpose,
        population=population,
        success_definition=SUCCESS_DEFINITION,
        exit_gate=EXIT_GATE,
        accuracy_bounds=accuracy_bounds,
        probe_populations=PROBES,
        analyzer_scope=analyzer_scope,
        statistical_requirements=statistical_requirements,
        pre_registration=pre_registration,
        declared_assumptions=declared_assumptions,
        content_hash=content_hash,
    )


def bind_provisioning(contract: Phase31CertificationContract, provisioning_event_ref: str) -> Phase31CertificationContract:
    # Rebuild with provisioning ref bound
    return build_contract_002(provisioning_event_ref=provisioning_event_ref)


CONTRACT_002 = build_contract_002()
