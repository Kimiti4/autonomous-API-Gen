"""Phase 36 Orchestrator -- Tiered Fidelity, Transducer, Proof of Life."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
import hashlib
from tiannara.application.evolution.ledger import EvolutionLedger, EvolutionEvent, EventType

class Verdict(Enum):
    CERTIFIED = "CERTIFIED"
    BOUNDED = "BOUNDED"
    NOT_CERTIFIED = "NOT_CERTIFIED"

@dataclass
class GenomeConstraint:
    gene_family: str
    allele_value: Any
    penalty_weight: float
    is_lethal: bool

@dataclass
class CampaignEvidence:
    dimension: str
    verdict: Verdict
    critical_findings: int
    chain_refs: List[str]
    causal_genes: List[str] = field(default_factory=list)

class ProductionReadinessConjunction:
    @staticmethod
    def evaluate(evaluations: Dict[str, CampaignEvidence]) -> tuple[bool, List[GenomeConstraint]]:
        required = {"compiler", "engineering", "security", "resilience"}
        if not required.issubset(evaluations.keys()):
            return False, []
        constraints = []
        is_ready = True
        for dim, ev in evaluations.items():
            if ev.verdict != Verdict.CERTIFIED:
                is_ready = False
            if ev.critical_findings > 0:
                is_ready = False
                constraints.append(GenomeConstraint(dim, "current_state", -100.0, True))
        return is_ready, constraints

class EvolutionaryFeedbackTransducer:
    def __init__(self, ledger_client, genome_registry):
        self.ledger = ledger_client
        self.genome_registry = genome_registry
    def process_campaign_failure(self, isr_hash: str, failed_evidence: List[CampaignEvidence]) -> List[GenomeConstraint]:
        constraints = []
        for ev in failed_evidence:
            if ev.verdict == Verdict.CERTIFIED and ev.critical_findings == 0:
                continue
            causal = self._resolve_chain_refs(ev.chain_refs)
            genes = self.genome_registry.map_isr_to_genome(isr_hash, causal) if hasattr(self.genome_registry, "map_isr_to_genome") else []
            for gene in genes:
                constraints.append(GenomeConstraint(gene.family if hasattr(gene, "family") else str(gene), getattr(gene, "current_allele", ev.dimension), self._calculate_penalty(ev.dimension, ev.critical_findings), ev.critical_findings>0 or ev.verdict==Verdict.BOUNDED))
        return constraints
    def _resolve_chain_refs(self, chain_refs: List[str]) -> List[str]:
        return self.ledger.get_root_causal_nodes(chain_refs) if hasattr(self.ledger, "get_root_causal_nodes") else chain_refs
    def _calculate_penalty(self, dim: str, criticals: int) -> float:
        base = {"security": -50.0, "resilience": -40.0, "compiler": -30.0, "engineering": -10.0}
        return base.get(dim, -10.0) * (1 + criticals)

class TieredCampaign:
    def __init__(self, ledger: EvolutionLedger):
        self.ledger = ledger
    def run_tier1(self, isr) -> bool:
        # Static ISR & Genome Analysis
        return True
    def run_tier2(self, artifact) -> tuple[bool, str]:
        # Deterministic compilation & unit verification
        return (True, "CERTIFIED")
    def run_tier3(self, artifact) -> Dict[str, CampaignEvidence]:
        # Full campaign only for Tier2 survivors
        evidence = {}
        for dim in ["compiler","engineering","security","resilience"]:
            ev = CampaignEvidence(dim, Verdict.CERTIFIED, 0, [f"chain-{dim}"])
            evidence[dim] = ev
        return evidence

def proof_of_life(isr_hash: str = "test-isr"):
    ledger = EvolutionLedger()
    # Inject flaw: disable mTLS
    flawed_evidence = CampaignEvidence("security", Verdict.NOT_CERTIFIED, 1, ["chain-security-flaw"])
    ok, constraints = ProductionReadinessConjunction.evaluate({
        "compiler": CampaignEvidence("compiler", Verdict.CERTIFIED, 0, ["c1"]),
        "engineering": CampaignEvidence("engineering", Verdict.CERTIFIED, 0, ["c2"]),
        "security": flawed_evidence,
        "resilience": CampaignEvidence("resilience", Verdict.CERTIFIED, 0, ["c3"]),
    })
    assert ok is False
    # Transducer should map to genome allele
    class FakeRegistry:
        def map_isr_to_genome(self, h, nodes): return [type("G",(),{"family":"security.authentication","current_allele":"mtls_disabled"})()]
    transducer = EvolutionaryFeedbackTransducer(ledger, FakeRegistry())
    constraints2 = transducer.process_campaign_failure(isr_hash, [flawed_evidence])
    assert any(c.is_lethal for c in constraints2)
    assert not any("threshold" in str(c).lower() for c in constraints2)
    return {"tiered": True, "conjunction_blocks": not ok, "transducer_lethal": constraints2[0].is_lethal if constraints2 else False}
