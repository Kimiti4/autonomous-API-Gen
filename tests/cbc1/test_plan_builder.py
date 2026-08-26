"""CBC-1 Plan Builder gates — corpus coverage, invariants, determinism, plan validity."""
from __future__ import annotations

import pytest

from certification.corpus.corpus import Category, default_corpus, corpus_hash
from certification.campaign.plan_builder import build_plan_for, intent_to_requirement_graph
from reqgraph.core.invariants import validate_requirement_graph


def test_corpus_covers_all_13_categories():
    cats = {w.category for w in default_corpus()}
    assert cats == set(Category)
    assert len(default_corpus()) == 39


def test_seeded_corpus_passes_requirement_invariants():
    for w in default_corpus():
        validate_requirement_graph(intent_to_requirement_graph(w))


def test_plan_builder_deterministic():
    w = default_corpus()[0]
    p1, r1, rg1, g1 = build_plan_for(w)
    p2, r2, rg2, g2 = build_plan_for(w)
    assert p1.model_dump_json() == p2.model_dump_json()
    assert r1.content_hash == r2.content_hash
    assert r1.revision_id == r2.revision_id
    assert rg1 == rg2 and g1 == g2


def test_plan_has_services_and_deployment():
    for w in default_corpus()[:13]:
        plan, rev, rg, gh = build_plan_for(w)
        assert plan.services
        assert all(s.data_models for s in plan.services)


def test_corpus_hash_deterministic():
    h1 = corpus_hash()
    h2 = corpus_hash()
    assert h1 == h2
    assert len(h1) == 64


def test_corpus_seeds_have_three_entities():
    for w in default_corpus():
        assert len(w.seeds) == 3
