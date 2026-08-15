from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from tiannara.application.synthesis.taxonomy import (
    StratificationTaxonomy,
    TaxonomyValidationError,
)

TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "config" / "taxonomy" / "v0.1.yaml"


def test_v01_loads_and_is_complete():
    taxonomy = StratificationTaxonomy.load(TAXONOMY_PATH)
    assert taxonomy.taxonomy_version == "0.1.0"
    assert len(taxonomy.axes.domain) == 5
    assert len(taxonomy.axes.complexity_tier) == 3


def test_profile_completeness_failure_is_explicit():
    raw = yaml.safe_load(TAXONOMY_PATH.read_text())
    del raw["profiles"]["domains"]["financial_services"]
    with pytest.raises(ValidationError, match="missing profiles"):
        StratificationTaxonomy.model_validate(raw)


def test_duplicate_axis_values_rejected():
    raw = yaml.safe_load(TAXONOMY_PATH.read_text())
    raw["axes"]["scale_tier"].append("small")
    with pytest.raises(ValidationError, match="duplicate"):
        StratificationTaxonomy.model_validate(raw)


def test_unknown_constraint_axis_rejected():
    raw = yaml.safe_load(TAXONOMY_PATH.read_text())
    raw["constraints"].append({"forbidden": {"nonexistent_axis": "x"}})
    with pytest.raises(ValidationError, match="unknown axis"):
        StratificationTaxonomy.model_validate(raw)


def test_constraint_violating_combination_is_filtered():
    from tiannara.application.synthesis.sampler import StratifiedSampler

    sampler = StratifiedSampler(StratificationTaxonomy.load(TAXONOMY_PATH))
    allowed = sampler.enumerate_strata()
    # The real-time + integration-none combination is forbidden by the
    # constraint; it must not enumerate.
    assert all(
        not (s.capability_class == "real_time" and s.integration_pattern == "none")
        for s in allowed
    )
    # Sanity: every allowed stratum is structurally valid for its profile set.
    assert len(allowed) == 1485
