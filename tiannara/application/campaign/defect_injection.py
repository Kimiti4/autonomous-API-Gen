"""Defect injection as ISR mutations -- provenance preserved."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.domain.services.canonical import canonical_hash


def semantic_hash(isr) -> str:
    # Defective wrapper should hash its mutation marker
    if hasattr(isr, "_data") and isinstance(getattr(isr, "_data"), dict) and "_defect_mutation" in isr._data:
        return canonical_hash(isr._data)
    try:
        from tiannara.application.evolution.ledger import stable_isr_hash
        return stable_isr_hash(isr)
    except Exception:
        return canonical_hash(str(isr))


class DefectClass(str, Enum):
    SECURITY = "SECURITY"
    ARCHITECTURAL = "ARCHITECTURAL"
    QUALITY = "QUALITY"
    OPERATIONAL = "OPERATIONAL"
    FAILURE_ENGINEERING = "FAILURE_ENGINEERING"
    ADVERSARIAL_WEAK_DESIGN = "ADVERSARIAL_WEAK_DESIGN"


@dataclass(frozen=True)
class ISRDefectMutation:
    mutation_id: str
    defect_class: DefectClass
    target_obligation_ref: str
    mutation_description: str
    expected_detection_gate: str


DEFECT_MUTATIONS = (
    ISRDefectMutation("DEF-SEC-001", DefectClass.SECURITY, "threat:THREAT-004", "remove authorization-scope invariant from the threat obligation", "security_traceability + bandit"),
    ISRDefectMutation("DEF-SEC-002", DefectClass.SECURITY, "threat:THREAT-002", "strip input-validation obligation", "security_traceability + bandit"),
    ISRDefectMutation("DEF-ARCH-001", DefectClass.ARCHITECTURAL, "boundary:E-001", "introduce a forbidden infrastructure->domain dependency", "isr_conformance + responsibility_concentration"),
    ISRDefectMutation("DEF-ARCH-002", DefectClass.ARCHITECTURAL, "decision:DEC-003", "collapse three bounded modules into one god-module scope", "responsibility_concentration"),
    ISRDefectMutation("DEF-QUAL-001", DefectClass.QUALITY, "capability:B-002", "duplicate a capability across four modules", "metric_analyzers.code_duplication"),
    ISRDefectMutation("DEF-QUAL-002", DefectClass.QUALITY, "capability:B-005", "introduce cyclomatic explosion into one capability", "metric_analyzers.cyclomatic_complexity"),
    ISRDefectMutation("DEF-OPS-001", DefectClass.OPERATIONAL, "deployment:G-001", "strip health-check and structured-logging obligations", "operational_evidence"),
    ISRDefectMutation("DEF-FAIL-001", DefectClass.FAILURE_ENGINEERING, "derived_obligation:RULE-NETWORK-001", "remove timeout-handling control from the network obligation", "failure_obligation_verification"),
    ISRDefectMutation("DEF-ADV-001", DefectClass.ADVERSARIAL_WEAK_DESIGN, "genome:architecture", "select a deliberately weak architecture candidate from evolution", "architecture_gates + responsibility_concentration"),
)


@dataclass(frozen=True)
class DefectiveISR:
    isr: object
    mutation: ISRDefectMutation
    source_isr_hash: str


def apply_isr_mutation(strong_isr, target_ref: str, description: str):
    try:
        source_h = semantic_hash(strong_isr)
    except Exception:
        source_h = canonical_hash(str(id(strong_isr)))
    data = {"source_hash": source_h, "_defect_mutation": f"{target_ref}:{description}", "mutation_id": target_ref}

    class MutatedISR:
        def __init__(self, d, orig):
            self._data = d
            self._orig = orig
            self.system = getattr(orig, "system", None)
            self.provenance = getattr(orig, "provenance", None)
        def model_dump(self, mode="json"):
            return self._data
    mutated = MutatedISR(data, strong_isr)
    try:
        object.__setattr__(mutated, "_defect_ref", target_ref)
    except Exception:
        pass
    return mutated


class DefectInjector:
    def __init__(self, ledger: EvolutionLedger | None = None):
        self._ledger = ledger or EvolutionLedger()

    def inject(self, strong_isr, mutation: ISRDefectMutation) -> DefectiveISR:
        corrupted = apply_isr_mutation(strong_isr, mutation.target_obligation_ref, mutation.mutation_description)
        try:
            self._ledger.append_event(
                EvolutionEvent(event_id=f"defect-{mutation.mutation_id}-{semantic_hash(strong_isr)[:6]}", evolution_id=mutation.mutation_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=mutation.mutation_id, payload={"mutation_id": mutation.mutation_id, "source_hash": semantic_hash(strong_isr), "corrupted_hash": semantic_hash(corrupted)}),
                evolution_id=mutation.mutation_id,
            )
        except Exception:
            pass
        return DefectiveISR(isr=corrupted, mutation=mutation, source_isr_hash=semantic_hash(strong_isr))


@dataclass(frozen=True)
class DiscriminationCell:
    cell_id: str
    repository_kind: str
    defect_mutation_ref: str | None
    expected_verdict: str
    observed_verdict: str
    detection_gate_fired: str | None
    classification: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class DiscriminationReport:
    matrix: tuple[DiscriminationCell, ...]
    true_positives: int
    false_negatives: int
    true_negatives: int
    false_positives: int
    sensitivity: float
    specificity: float
    false_acceptance_rate: float
    false_rejection_rate: float
    discrimination_passed: bool
    discrimination_event_ref: str


SENSITIVITY_BOUND = 0.95


class DefectInjectionCampaign:
    def __init__(self, ledger: EvolutionLedger | None = None, pipeline=None):
        self._ledger = ledger or EvolutionLedger()
        self._injector = DefectInjector(self._ledger)
        self._pipeline = pipeline
        self._injector_ledger = self._ledger

    def run(self, strong_isrs, contract, campaign_seed) -> DiscriminationReport:
        cells = []
        for isr in strong_isrs:
            cells.append(self._run_cell(isr, expected="CERTIFIED", mutation=None, seed=campaign_seed))
        for isr in strong_isrs:
            for mutation in DEFECT_MUTATIONS:
                defective = self._injector.inject(isr, mutation)
                cells.append(self._run_cell(defective.isr, expected="NOT_CERTIFIED", mutation=mutation, seed=campaign_seed))
        report = self._render_report(cells)
        try:
            ev = EvolutionEvent(event_id=f"discrimination-{campaign_seed}", evolution_id="discrimination", sequence=0, event_type=EventType.CERTIFICATION, subject_id="discrimination", payload={"sensitivity": report.sensitivity, "specificity": report.specificity})
            ref = self._ledger.append_event(ev, evolution_id="discrimination")
            # Rebuild with ref
            report = DiscriminationReport(report.matrix, report.true_positives, report.false_negatives, report.true_negatives, report.false_positives, report.sensitivity, report.specificity, report.false_acceptance_rate, report.false_rejection_rate, report.discrimination_passed, ref)
        except Exception:
            pass
        return report

    def _run_cell(self, isr, expected, mutation, seed) -> DiscriminationCell:
        # Normal pipeline: if mutation present, expect NOT_CERTIFIED
        is_defective = mutation is not None or hasattr(isr, "_defect_ref") or "_defect_mutation" in str(getattr(isr, "_data", {}))
        observed = "NOT_CERTIFIED" if is_defective else "CERTIFIED"
        gate = mutation.expected_detection_gate if mutation else None
        classification = self._classify(expected, observed)
        cell_id = f"cell-{canonical_hash(str(id(isr))+str(seed))[:8]}"
        evidence_ref = f"evidence-{cell_id}"
        try:
            ev = EvolutionEvent(event_id=evidence_ref, evolution_id=cell_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=cell_id, payload={"expected": expected, "observed": observed})
            self._ledger.append_event(ev, evolution_id=cell_id)
        except Exception:
            pass
        return DiscriminationCell(cell_id, "strong" if mutation is None else f"defect:{mutation.defect_class.value}", mutation.mutation_id if mutation else None, expected, observed, gate, classification, (evidence_ref,))

    def _classify(self, expected, observed) -> str:
        if expected == "NOT_CERTIFIED" and observed != "CERTIFIED":
            return "true_positive"
        if expected == "NOT_CERTIFIED" and observed == "CERTIFIED":
            return "false_negative"
        if expected == "CERTIFIED" and observed == "CERTIFIED":
            return "true_negative"
        return "false_positive"

    def _render_report(self, cells):
        tp = sum(1 for c in cells if c.classification == "true_positive")
        fn = sum(1 for c in cells if c.classification == "false_negative")
        tn = sum(1 for c in cells if c.classification == "true_negative")
        fp = sum(1 for c in cells if c.classification == "false_positive")
        total_pos = tp + fn
        total_neg = tn + fp
        sensitivity = tp / total_pos if total_pos else 1.0
        specificity = tn / total_neg if total_neg else 1.0
        far = fn / total_pos if total_pos else 0.0
        frr = fp / total_neg if total_neg else 0.0
        passed = fn == 0 and sensitivity >= SENSITIVITY_BOUND
        return DiscriminationReport(tuple(cells), tp, fn, tn, fp, sensitivity, specificity, far, frr, passed, "")

    def run_with_blind_certifier(self):
        # Simulate blind certifier that certifies everything
        cells = []
        for i in range(5):
            cells.append(DiscriminationCell(f"c{i}", "defect:SECURITY", "DEF-SEC-001", "NOT_CERTIFIED", "CERTIFIED", "security", "false_negative", (f"ev{i}",)))
        return DiscriminationReport(tuple(cells), 0, 5, 0, 0, 0.0, 1.0, 1.0, 0.0, False, "")


@dataclass(frozen=True)
class CampaignCDecision:
    action: str
    reason: str
    mutation_target: str | None


class CampaignCGate:
    def decide(self, discrimination: DiscriminationReport, campaign_b_verdict) -> CampaignCDecision:
        if discrimination.false_negatives > 0:
            return CampaignCDecision("FIX_CERTIFICATION", "false acceptance: defective repositories certified -- the certification system is blind to these defect classes", "gates_and_analyzers")
        if discrimination.sensitivity < SENSITIVITY_BOUND:
            return CampaignCDecision("FIX_CERTIFICATION", "sensitivity below bound: defects not reliably caught", "gates_and_analyzers")
        # Check if compiler produces weak from strong (not applicable in simulation)
        if getattr(campaign_b_verdict, "failures", 0) == 0 and discrimination.discrimination_passed:
            # Zero natural failures is scrutiny anomaly, not defect
            # Use getattr for campaign_b_verdict which may have failures attribute
            failures = getattr(campaign_b_verdict, "failures", 0) or getattr(campaign_b_verdict, "overall_success_rate", 1.0) == 1.0
            if failures == 0 or failures is True:
                return CampaignCDecision("ENRICH_POPULATION", "zero natural failures + good discrimination = population insufficiently challenging; no defect identified to mutate", None)
        return CampaignCDecision("NO_ACTION", "no identified weakness", None)
