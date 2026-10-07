"""Complete Bucket 2 mode-specific mutation operator set."""
from __future__ import annotations
from .specialized_mutations import _spec
from .architecture_mutation import domain_operator

def _capability(mutation_id, domain, paths, rationale, evidence, operator, properties, risk):
    return _spec(domain_operator(mutation_id, domain, paths, rationale, evidence, operator), properties, risk)

def generate_mutation(mutation_id, paths, rationale, evidence, operator):
    return _capability(mutation_id, "generate", paths, rationale, evidence, operator, ("generation-integrity","requirement-traceability","end-to-end-verification"), "high")
def maintain_mutation(mutation_id, paths, rationale, evidence, operator):
    return _capability(mutation_id, "maintain", paths, rationale, evidence, operator, ("maintenance-safety","regression-preservation","operational-integrity"), "high")
def improve_mutation(mutation_id, paths, rationale, evidence, operator):
    return _capability(mutation_id, "improve", paths, rationale, evidence, operator, ("improvement-correctness","regression-preservation","requirement-traceability"), "high")
def seo_mutation(mutation_id, paths, rationale, evidence, operator):
    return _capability(mutation_id, "seo", paths, rationale, evidence, operator, ("seo","metadata-correctness","crawlability","content-integrity"), "medium")
def cross_stack_mutation(mutation_id, paths, rationale, evidence, operator):
    return _capability(mutation_id, "crossstack", paths, rationale, evidence, operator, ("cross-domain-contracts","end-to-end-flow","integration-safety"), "critical")
