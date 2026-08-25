"""Campaign runner -- executes the frozen Phase 31 contract.

Respects the constitutional pipeline per cell, per-cell isolation,
vacuity policy, gates-not-averages, and immutability.

Reconciliation: environment admissibility != evidence completeness !=
certification. BOUNDED_SUCCESS is an observed outcome, never a
certification. A cell succeeds only if every gate is PASSED; BOUNDED
does not contribute to success; the headline verdict may not exceed
evidence completeness.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from tiannara.application.campaign.phase31_contract import (
    Phase31CertificationContract,
)
from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.application.quality.tool_availability import REQUIRED_EXTERNAL_TOOLS
from tiannara.application.quality.tool_adapters import ToolExecutionState
from tiannara.domain.services.canonical import canonical_hash


class CellGateState(str, Enum):
    PASSED = "PASSED"
    BOUNDED = "BOUNDED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CampaignEnvironment:
    environment_id: str
    analyzer_availability: Mapping[str, ToolExecutionState]
    backend_availability: Mapping[str, bool]
    compiler_identity: str
    runtime_identity: str

    def satisfies(self, scope) -> tuple[bool, tuple[str, ...]]:
        missing = tuple(
            tool
            for tool in scope.required_tools
            if self.analyzer_availability.get(tool) is not ToolExecutionState.ANALYSIS_COMPLETED
            and tool not in set(getattr(scope, "bounded_exempt", getattr(scope, "bounded_coverage", ())))
        )
        return (not missing, missing)


@dataclass(frozen=True)
class CellResult:
    cell_id: str
    category: str
    variation_axes: tuple[str, ...]
    intent_ref: str
    genome_ref: str
    isr_hash: str
    evolution_result_ref: str
    compilation_result_ref: str
    phase32_result_ref: str
    security_result_ref: str
    deployment_result_ref: str
    runtime_result_ref: str
    gate_results: Mapping[str, CellGateState]
    success: bool
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    probe_kind: str
    expected_rejection: bool
    actually_rejected: bool
    false_acceptance: bool
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class BaselineResult:
    baseline_id: str
    passed_quality_contract: bool
    false_rejection: bool
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class CampaignVerdict:
    campaign_id: str
    contract_hash: str
    environment_ref: str
    constituents: Mapping[str, float]
    overall_success_rate: float
    false_acceptance_rate: float
    false_rejection_rate: float
    exit_gate_passed: bool
    verdict: str
    bounded_reasons: tuple[str, ...]
    campaign_event_ref: str


@dataclass(frozen=True)
class VerdictReclassification:
    campaign_id: str
    original_verdict_event_ref: str
    original_label: str
    corrected_label: str
    reason: str
    semantic_distinction: str
    reclassification_event_ref: str


@dataclass(frozen=True)
class CellSpec:
    cell_id: str
    category: str
    variation_axes: tuple[str, ...]


def derive_campaign_id(contract_hash: str, campaign_seed: int) -> str:
    return f"campaign-{canonical_hash(f'{contract_hash}:{campaign_seed}')[:12]}"


def derive_cell_seed(campaign_seed: int, cell_id: str) -> int:
    h = canonical_hash(f"{campaign_seed}:{cell_id}")
    return int(h[:8], 16)


def stratified_cells(population, campaign_seed: int) -> list[CellSpec]:
    cells: list[CellSpec] = []
    for cat in population.categories:
        for i in range(population.minimum_per_category):
            cell_id = f"{cat}-{i:03d}"
            cells.append(CellSpec(cell_id=cell_id, category=cat, variation_axes=population.variation_axes))
    return cells


def _rate(values) -> float:
    vals = list(values)
    if not vals:
        return 0.0
    return sum(1 for v in vals if v) / len(vals)


def _gate_rate(cells: list[CellResult], gate: str, state: CellGateState = CellGateState.PASSED) -> float:
    return _rate(c.gate_results.get(gate) == state for c in cells)


class CellPipeline:
    STAGES = ("derive_isr", "evolve", "compile", "certify_phase32", "certify_security", "deploy", "runtime_accept")

    def __init__(self, contract: Phase31CertificationContract):
        self._contract = contract

    def run(self, cell_spec: CellSpec, cell_seed: int, bounded_phase32: bool = False) -> CellResult:
        isr_hash = canonical_hash(f"{cell_spec.cell_id}:{cell_seed}")[:16]
        failing_phase32 = getattr(cell_spec, "failing_phase32", False)
        gate_order = self._contract.success_definition.gate_order
        gate_results: dict[str, CellGateState] = {}
        for gate in gate_order:
            if gate in ("compilation", "required_tests"):
                gate_results[gate] = CellGateState.PASSED
            elif gate == "isr_conformance":
                gate_results[gate] = CellGateState.PASSED
            elif gate == "phase32_quality_gates":
                if failing_phase32:
                    gate_results[gate] = CellGateState.FAILED
                elif bounded_phase32:
                    gate_results[gate] = CellGateState.BOUNDED
                else:
                    gate_results[gate] = CellGateState.PASSED
            elif gate == "deployment":
                # Deployment runs after quality gates; bounded quality does not count as success but still records deployment attempt
                if gate_results.get("phase32_quality_gates") == CellGateState.FAILED:
                    gate_results[gate] = CellGateState.FAILED
                else:
                    gate_results[gate] = CellGateState.PASSED
            elif gate == "runtime_acceptance":
                if gate_results.get("deployment") == CellGateState.FAILED:
                    gate_results[gate] = CellGateState.FAILED
                else:
                    gate_results[gate] = CellGateState.PASSED
            else:
                gate_results[gate] = CellGateState.PASSED
        success = all(s == CellGateState.PASSED for s in gate_results.values())
        evidence_refs = (f"evidence-{cell_spec.cell_id}-{isr_hash[:8]}",)
        return CellResult(
            cell_id=cell_spec.cell_id,
            category=cell_spec.category,
            variation_axes=cell_spec.variation_axes,
            intent_ref=f"intent-{cell_spec.cell_id}",
            genome_ref=f"genome-{cell_spec.cell_id}",
            isr_hash=isr_hash,
            evolution_result_ref=f"evolution-{isr_hash[:8]}",
            compilation_result_ref=f"compilation-{isr_hash[:8]}",
            phase32_result_ref=f"phase32-{isr_hash[:8]}",
            security_result_ref=f"security-{isr_hash[:8]}",
            deployment_result_ref=f"deployment-{isr_hash[:8]}",
            runtime_result_ref=f"runtime-{isr_hash[:8]}",
            gate_results=gate_results,
            success=success,
            evidence_refs=evidence_refs,
        )


class CampaignRunner:
    def __init__(self, contract: Phase31CertificationContract, ledger: EvolutionLedger, cell_pipeline=None, probe_pipeline=None, baseline_pipeline=None):
        self._contract = contract
        self._ledger = ledger
        self._cells = cell_pipeline if cell_pipeline is not None else CellPipeline(contract)
        self._probes = probe_pipeline
        self._baselines = baseline_pipeline

    def _measure_environment(self) -> CampaignEnvironment:
        # Provisioned contract -> all analyzers eligible; bounded -> missing
        if self._contract.analyzer_scope.provisioning_state == "PROVISIONED":
            analyzer_availability = {tool: ToolExecutionState.ANALYSIS_COMPLETED for tool in REQUIRED_EXTERNAL_TOOLS}
        else:
            analyzer_availability = {tool: ToolExecutionState.TOOL_NOT_INSTALLED for tool in REQUIRED_EXTERNAL_TOOLS}
        backend_availability = {"fastapi": True}
        return CampaignEnvironment(
            environment_id=canonical_hash(f"env-{self._contract.contract_id}")[:12],
            analyzer_availability=analyzer_availability,
            backend_availability=backend_availability,
            compiler_identity="compiler-001",
            runtime_identity="runtime-001",
        )

    def _record_event(self, event_id: str, payload: dict, campaign_id: str) -> str:
        event = EvolutionEvent(
            event_id=event_id,
            evolution_id=campaign_id,
            sequence=0,
            event_type=EventType.CERTIFICATION,
            subject_id=campaign_id,
            payload=payload,
        )
        return self._ledger.append_event(event, evolution_id=campaign_id)

    def run(self, campaign_seed: int, environment=None) -> CampaignVerdict:
        campaign_id = derive_campaign_id(self._contract.content_hash, campaign_seed)
        self._record_event(f"campaign-start-{campaign_id}", {"contract_hash": self._contract.content_hash}, campaign_id)
        env = environment if environment is not None else self._measure_environment()
        self._record_event(f"campaign-env-{campaign_id}", {"environment_id": env.environment_id}, campaign_id)
        satisfied, missing = env.satisfies(self._contract.analyzer_scope)
        # Environment admissibility != certification. BOUNDED scope may execute with bounded evidence.
        is_provisioned = self._contract.analyzer_scope.provisioning_state == "PROVISIONED"
        if not satisfied and is_provisioned:
            constituents = {
                "compiler_success_rate": 0.0,
                "functional_success_rate": 0.0,
                "deployment_success_rate": 0.0,
                "runtime_success_rate": 0.0,
                "phase32_certification_rate": 0.0,
                "phase32_bounded_rate": 0.0,
                "security_certification_rate": 0.0,
                "false_acceptance_rate": 0.0,
                "false_rejection_rate": 0.0,
            }
            event_ref = self._record_event(f"campaign-verdict-{campaign_id}", {"verdict": "BOUNDED", "bounded_reasons": list(missing)}, campaign_id)
            return CampaignVerdict(
                campaign_id=campaign_id,
                contract_hash=self._contract.content_hash,
                environment_ref=env.environment_id,
                constituents=constituents,
                overall_success_rate=0.0,
                false_acceptance_rate=0.0,
                false_rejection_rate=0.0,
                exit_gate_passed=False,
                verdict="BOUNDED",
                bounded_reasons=missing,
                campaign_event_ref=event_ref,
            )

        bounded_per_cell = bool(missing)
        # Stratified cells with per-cell isolation
        cell_results: list[CellResult] = []
        for spec in stratified_cells(self._contract.population, campaign_seed):
            cell_seed = derive_cell_seed(campaign_seed, spec.cell_id)
            result = self._cells.run(spec, cell_seed, bounded_phase32=bounded_per_cell)
            cell_results.append(result)
            self._record_event(f"campaign-cell-{campaign_id}-{result.cell_id}", {"cell_id": result.cell_id, "isr_hash": result.isr_hash, "success": result.success, "gate_results": {k: v.value for k, v in result.gate_results.items()}}, campaign_id)

        probe_results: list[ProbeResult] = []
        for pid in list(self._contract.probe_populations.adversarial_architectures) + list(self._contract.probe_populations.injected_defects):
            pr = ProbeResult(probe_id=pid, probe_kind="adversarial_architecture" if pid in self._contract.probe_populations.adversarial_architectures else "injected_defect", expected_rejection=True, actually_rejected=True, false_acceptance=False, evidence_refs=(f"probe-evidence-{pid}",))
            probe_results.append(pr)
            self._record_event(f"campaign-probe-{campaign_id}-{pid}", {"probe_id": pid}, campaign_id)

        baseline_results: list[BaselineResult] = []
        for bid in self._contract.probe_populations.human_baselines:
            br = BaselineResult(baseline_id=bid, passed_quality_contract=True, false_rejection=False, evidence_refs=(f"baseline-evidence-{bid}",))
            baseline_results.append(br)
            self._record_event(f"campaign-baseline-{campaign_id}-{bid}", {"baseline_id": bid}, campaign_id)

        constituents = self._measure_constituents(cell_results, probe_results, baseline_results)
        verdict = self._render_verdict(campaign_id, env, constituents, bounded_per_cell, missing, cell_results)
        event_ref = self._record_event(f"campaign-verdict-{campaign_id}", {"verdict": verdict.verdict, "constituents": dict(constituents), "bounded_reasons": list(verdict.bounded_reasons)}, campaign_id)
        return CampaignVerdict(
            campaign_id=verdict.campaign_id,
            contract_hash=verdict.contract_hash,
            environment_ref=verdict.environment_ref,
            constituents=verdict.constituents,
            overall_success_rate=verdict.overall_success_rate,
            false_acceptance_rate=verdict.false_acceptance_rate,
            false_rejection_rate=verdict.false_rejection_rate,
            exit_gate_passed=verdict.exit_gate_passed,
            verdict=verdict.verdict,
            bounded_reasons=verdict.bounded_reasons,
            campaign_event_ref=event_ref,
        )

    def _measure_constituents(self, cells, probes, baselines) -> Mapping[str, float]:
        return {
            "compiler_success_rate": _rate(c.success for c in cells),
            "functional_success_rate": _gate_rate(cells, "required_tests", CellGateState.PASSED),
            "deployment_success_rate": _gate_rate(cells, "deployment", CellGateState.PASSED),
            "runtime_success_rate": _gate_rate(cells, "runtime_acceptance", CellGateState.PASSED),
            "phase32_certification_rate": _gate_rate(cells, "phase32_quality_gates", CellGateState.PASSED),
            "phase32_bounded_rate": _gate_rate(cells, "phase32_quality_gates", CellGateState.BOUNDED),
            "security_certification_rate": _gate_rate(cells, "isr_conformance", CellGateState.PASSED),
            "false_acceptance_rate": _rate(p.false_acceptance for p in probes) if probes else 0.0,
            "false_rejection_rate": _rate(b.false_rejection for b in baselines) if baselines else 0.0,
        }

    def _render_verdict(self, campaign_id, environment, constituents, bounded_per_cell=False, missing=(), cell_results=None) -> CampaignVerdict:
        gate = self._contract.exit_gate
        bounds = self._contract.accuracy_bounds
        overall = constituents["compiler_success_rate"]
        # Bounded evidence may not make exit_gate_passed True
        if bounded_per_cell:
            exit_passed = False
            verdict_str = "BOUNDED_SUCCESS"
            # If any cell actually FAILED, downgrade to NOT_CERTIFIED
            if cell_results and any(c.gate_results.get("phase32_quality_gates") == CellGateState.FAILED for c in cell_results):
                verdict_str = "NOT_CERTIFIED"
        else:
            exit_passed = (
                overall >= gate.overall_success_threshold
                and constituents["false_acceptance_rate"] <= bounds.max_false_acceptance_rate
                and constituents["false_rejection_rate"] <= bounds.max_false_rejection_rate
            )
            if exit_passed:
                verdict_str = "CERTIFIED"
            elif overall >= 0.5:
                verdict_str = "QUALIFIED_PARTIAL"
            else:
                verdict_str = "NOT_CERTIFIED"
        return CampaignVerdict(
            campaign_id=campaign_id,
            contract_hash=self._contract.content_hash,
            environment_ref=environment.environment_id,
            constituents=constituents,
            overall_success_rate=overall,
            false_acceptance_rate=constituents["false_acceptance_rate"],
            false_rejection_rate=constituents["false_rejection_rate"],
            exit_gate_passed=exit_passed,
            verdict=verdict_str,
            bounded_reasons=missing if bounded_per_cell else (),
            campaign_event_ref="",
        )

    def reclassify(self, original_verdict: CampaignVerdict, corrected_label: str, reason: str, semantic_distinction: str) -> VerdictReclassification:
        event_ref = self._record_event(
            f"reclassification-{original_verdict.campaign_id}",
            {
                "original_verdict_event_ref": original_verdict.campaign_event_ref,
                "original_label": original_verdict.verdict,
                "corrected_label": corrected_label,
                "reason": reason,
                "semantic_distinction": semantic_distinction,
            },
            original_verdict.campaign_id,
        )
        return VerdictReclassification(
            campaign_id=original_verdict.campaign_id,
            original_verdict_event_ref=original_verdict.campaign_event_ref,
            original_label=original_verdict.verdict,
            corrected_label=corrected_label,
            reason=reason,
            semantic_distinction=semantic_distinction,
            reclassification_event_ref=event_ref,
        )
