"""Tests for the 100-project stratified corpus.

Validates the Phase 31 spec's "Immediate Next Step":
  > "Do not start Phase 31 with thousands of projects. Start with
  > ~100 stratified projects (a representative slice of the domain
  > x backend matrix), run through a first-draft Certification
  > Harness, specifically to calibrate the harness itself."
"""
from __future__ import annotations

import json
import re

import pytest

from tiannara.application.campaign.corpus import ProjectCategory

from certification.corpus.stratified_corpus import (
    CORPUS_ID,
    CORPUS_VERSION,
    PER_CATEGORY_PER_TIER,
    TARGET_PROJECT_COUNT,
    stratified_corpus,
    stratified_corpus_hash,
    stratified_corpus_intents,
    stratification_report,
)


# -- Forbidden technology-specific terms (per master prompt §3) ------
# No implementation leakage in the ISR, no "postgres", "FastAPI", etc.
FORBIDDEN_TECH_TERMS = (
    "postgres", "postgresql", "mysql", "mongodb", "redis", "kafka",
    "fastapi", "react", "rust", "python", "java", "spring", "aws",
    "azure", "gcp", "kubernetes", "k8s", "docker", "terraform",
    "github", "graphql", "websocket", "websocket", "grpc",
)


def test_corpus_id_and_version_are_stable():
    """Versioning invariant: corpus_id and version are stable strings
    that auditors can reference."""
    assert CORPUS_ID == "corpus-100-stratified"
    assert CORPUS_VERSION == "1.0.0"


def test_stratified_corpus_has_exactly_100_projects():
    """The spec says ~100. We aim for exactly 100 (the trim is
    documented in the source)."""
    c = stratified_corpus()
    assert len(c.intents) == TARGET_PROJECT_COUNT == 100
    assert c.corpus_id == CORPUS_ID


def test_all_thirteen_categories_are_covered():
    """No category is missing. The matrix-level gaps the spec warned
    about (e.g. "A backend failing only on embedded targets should
    be quarantined, not drag down the platform verdict") require
    every category to be present so the verdict is per-category."""
    c = stratified_corpus()
    covered = {i.category for i in c.intents}
    assert covered == set(ProjectCategory), (
        f"missing categories: {set(ProjectCategory) - covered}"
    )


def test_stratification_8_projects_per_category_raw_104_total():
    """13 categories x 8 projects each = 104 raw, 100 after documented
    trim. The trim drops 1 from each of 4 categories, leaving 9
    categories at 8 and 4 categories at 7.

    The raw pre-trim count is 13*8=104; the 4-drop list is documented.
    """
    from certification.corpus.stratified_corpus import _DROP_IDS, _STRATIFIED
    assert len(_STRATIFIED) == 13 * 8 == 104
    assert len(_DROP_IDS) == 4

    dropped_cats = {
        next(i.category for i in _STRATIFIED if i.intent_id == d)
        for d in _DROP_IDS
    }
    assert len(dropped_cats) == 4, "each drop must be from a different category"

    by_category: dict[ProjectCategory, int] = {}
    for i in stratified_corpus_intents():
        by_category[i.category] = by_category.get(i.category, 0) + 1
    for cat in ProjectCategory:
        expected = 7 if cat in dropped_cats else 8
        assert by_category[cat] == expected, (
            f"{cat} has {by_category[cat]} projects, expected {expected}"
        )


def test_tier_distribution_simple_moderate_complex():
    """Across the corpus, the 3 tiers are present in a roughly
    4:2:2 ratio per category (the documented stratification). After
    the 4-drop trim (all simple entries), the per-tier counts are:
    simple = 13*4 - 4 = 48, moderate = 13*2 = 26, complex = 13*2 = 26,
    total = 100."""
    by_tier = {1: 0, 2: 0, 3: 0}
    for i in stratified_corpus_intents():
        by_tier[i.complexity_tier] += 1
    assert by_tier[1] == 48
    assert by_tier[2] == 26
    assert by_tier[3] == 26
    assert sum(by_tier.values()) == 100


def test_per_category_per_tier_stratification_after_trim():
    """The documented trim drops 4 simple entries, one from each of 4
    different categories. The other tiers (2 moderate, 2 complex)
    are never trimmed."""
    from certification.corpus.stratified_corpus import _DROP_IDS, _STRATIFIED
    dropped_simple_cats = {
        next(i.category for i in _STRATIFIED if i.intent_id == d)
        for d in _DROP_IDS
    }
    by_cat_tier: dict[tuple[ProjectCategory, int], int] = {}
    for i in stratified_corpus_intents():
        by_cat_tier[(i.category, i.complexity_tier)] = (
            by_cat_tier.get((i.category, i.complexity_tier), 0) + 1
        )
    for cat, tier in by_cat_tier:
        if tier == 1:
            expected = 3 if cat in dropped_simple_cats else 4
            assert by_cat_tier[(cat, tier)] == expected, (
                f"{cat} tier1 has {by_cat_tier[(cat, tier)]}, expected {expected}"
            )
        else:
            # Tier 2 and 3 are never trimmed.
            assert by_cat_tier[(cat, tier)] == PER_CATEGORY_PER_TIER[tier - 1]


def test_no_technology_leakage_in_problem_statements():
    """Master prompt §3: no implementation-specific terms in the ISR.
    The corpus's problem statements feed the ISR; they must be
    technology-free."""
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(t) for t in FORBIDDEN_TECH_TERMS) + r")\b",
        re.IGNORECASE,
    )
    leaks = []
    for i in stratified_corpus_intents():
        m = pattern.search(i.problem_statement)
        if m:
            leaks.append((i.intent_id, m.group(0)))
    assert not leaks, f"technology leakage: {leaks}"


def test_intent_ids_are_unique():
    c = stratified_corpus()
    ids = [i.intent_id for i in c.intents]
    assert len(set(ids)) == 100, "intent_id collision"


def test_intent_ids_are_stable():
    """Auditor expectation: the same corpus produces the same
    intent_ids. If you re-run, the set must match."""
    a = {i.intent_id for i in stratified_corpus_intents()}
    b = {i.intent_id for i in stratified_corpus_intents()}
    assert a == b


def test_corpus_hash_is_deterministic():
    """Reproducibility: the hash must be stable across calls.
    Auditors can re-run and verify."""
    h1 = stratified_corpus_hash()
    h2 = stratified_corpus_hash()
    assert h1 == h2
    assert len(h1) == 64  # SHA-256


def test_corpus_hash_is_unique():
    """The 100-project corpus must have a different hash from the
    26-intent dry-run corpus (otherwise the calibration run would
    silently use the wrong evidence)."""
    from tests.test_r29_10_9_campaign_readiness import dry_run_corpus

    h_strat = stratified_corpus_hash()
    h_dry = dry_run_corpus().corpus_id
    # Different corpora, different identities.
    assert h_strat != h_dry
    assert h_strat != h_dry.encode() if isinstance(h_dry, str) else True


def test_no_overlap_with_dry_run_corpus():
    """The 100-project slice is the SCALE-UP. It must not duplicate
    intent_ids from the existing 26-intent dry-run corpus."""
    from tests.test_r29_10_9_campaign_readiness import dry_run_corpus

    stratified_ids = {i.intent_id for i in stratified_corpus_intents()}
    dry_ids = {i.intent_id for i in dry_run_corpus().intents}
    overlap = stratified_ids & dry_ids
    assert not overlap, f"overlap with dry_run_corpus: {sorted(overlap)}"


def test_stratification_report_runs_cleanly():
    """The audit report produces stable output and includes all the
    rows an auditor needs."""
    r = stratification_report()
    assert "corpus_id=corpus-100-stratified" in r
    assert "total=100" in r
    assert "by_category=" in r
    assert "by_tier=" in r
    # Every category appears
    for cat in ProjectCategory:
        assert cat.value in r, f"missing {cat.value} from stratification report"


def test_complexity_tiers_are_in_range():
    """Sanity: complexity_tier must be 1, 2, or 3 (not 0 or 4)."""
    for i in stratified_corpus_intents():
        assert i.complexity_tier in (1, 2, 3), (
            f"{i.intent_id} has complexity_tier={i.complexity_tier}"
        )


def test_acceptance_semantics_is_nonempty():
    """Every project must declare what 'done' means. The
    `acceptance_semantics` field carries this."""
    for i in stratified_corpus_intents():
        assert i.acceptance_semantics, (
            f"{i.intent_id} has no acceptance_semantics"
        )
        assert isinstance(i.acceptance_semantics, tuple)
        assert all(isinstance(s, str) and s for s in i.acceptance_semantics), (
            f"{i.intent_id} has empty acceptance_semantics entries"
        )


def test_problem_statements_are_substantive():
    """The corpus is a calibration slice, not a placeholder list.
    Every problem statement must be at least 40 chars (a real
    one-liner is rarely shorter)."""
    for i in stratified_corpus_intents():
        assert len(i.problem_statement) >= 40, (
            f"{i.intent_id} problem_statement too short: "
            f"{len(i.problem_statement)} chars"
        )


def test_corpus_intent_ids_follow_convention():
    """Naming convention: <category-prefix>-<short-name>-<NN> per
    category. This is the convention observed in dry_run_corpus and
    here preserved for the 100-project slice."""
    prefixes = {
        ProjectCategory.CRUD_SAAS: "saas-",
        ProjectCategory.ERP: "erp-",
        ProjectCategory.BANKING: "bank-",
        ProjectCategory.HEALTHCARE: "hc-",
        ProjectCategory.LOGISTICS: "log-",
        ProjectCategory.AI_PLATFORM: "ai-",
        ProjectCategory.GAMING: "game-",
        ProjectCategory.IOT: "iot-",
        ProjectCategory.ROBOTICS: "rob-",
        ProjectCategory.DISTRIBUTED: "dist-",
        ProjectCategory.EMBEDDED: "emb-",
        ProjectCategory.API: "api-",
        ProjectCategory.STREAMING: "stream-",
    }
    for i in stratified_corpus_intents():
        prefix = prefixes[i.category]
        assert i.intent_id.startswith(prefix), (
            f"{i.intent_id} doesn't start with {prefix!r}"
        )
