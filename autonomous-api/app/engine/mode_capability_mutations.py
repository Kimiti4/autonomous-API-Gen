"""Complete Bucket 2 mode-specific mutation operator set."""

from __future__ import annotations

from .specialized_mutations import _spec
from .architecture_mutation import domain_operator


def _capability(mutation_id, domain, paths, rationale, evidence, operator, properties, risk):
    return _spec(domain_operator(mutation_id, domain, paths, rationale, evidence, operator), properties, risk)


def generate_mutation(*args):
    return _capability(*args, "generation-integrity", "requirement-traceability", "end-to-end-verification", risk="high")


def maintain_mutation(*args):
    return _capability(*args, "maintenance-safety", "regression-preservation", "operational-integrity", risk="high")


def improve_mutation(*args):
    return _capability(*args, "improvement-correctness", "regression-preservation", "requirement-traceability", risk="high")


def seo_mutation(*args):
    return _capability(*args, "seo", "metadata-correctness", "crawlability", "content-integrity", risk="medium")


def cross_stack_mutation(*args):
    return _capability(*args, "crossstack", "cross-domain-contracts", "end-to-end-flow", "integration-safety", risk="critical")
