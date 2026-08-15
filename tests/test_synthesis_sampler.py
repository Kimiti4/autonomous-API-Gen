from pathlib import Path

from tiannara.application.synthesis.sampler import DefectRates, StratifiedSampler
from tiannara.application.synthesis.taxonomy import StratificationTaxonomy
from tiannara.domain.models.requirement_graph import RequirementKind
from tiannara.domain.models.requirement_sketch import PlantedDefectKind

TAXONOMY_PATH = Path(__file__).resolve().parents[1] / "config" / "taxonomy" / "v0.1.yaml"


def _taxonomy() -> StratificationTaxonomy:
    return StratificationTaxonomy.load(TAXONOMY_PATH)


def _sampler(**rates) -> StratifiedSampler:
    return StratifiedSampler(_taxonomy(), DefectRates(**rates) if rates else None)


def test_stratum_space_is_constraint_filtered():
    sampler = _sampler()
    strata = sampler.enumerate_strata()
    # 5 x 3 x 4 x 3 x 3 x 3 = 1620; forbidden (integration=none x
    # capability_class=real_time) removes 5 x 3 x 1 x 3 x 1 x 3 = 135 -> 1485.
    assert len(strata) == 1485
    assert all(
        not (s.integration_pattern == "none" and s.capability_class == "real_time")
        for s in strata
    )


def test_same_seed_is_byte_identical():
    sampler = _sampler()
    first = [s.content_hash() for s in sampler.sample(25, seed=42)]
    second = [
        s.content_hash()
        for s in StratifiedSampler(_taxonomy()).sample(25, seed=42)
    ]
    assert first == second


def test_different_seed_differs():
    sampler = _sampler()
    a = [s.content_hash() for s in sampler.sample(25, seed=1)]
    b = [s.content_hash() for s in sampler.sample(25, seed=2)]
    assert a != b


def test_coverage_first_no_repeat_before_full_cycle():
    sampler = _sampler()
    strata_count = len(sampler.enumerate_strata())
    corpus = sampler.sample(strata_count, seed=7)
    keys = [s.assignment.key() for s in corpus]
    assert len(set(keys)) == strata_count
    assert all(s.provenance.epoch == 0 for s in corpus)


def test_wrap_increments_epoch():
    sampler = _sampler()
    strata_count = len(sampler.enumerate_strata())
    corpus = sampler.sample(strata_count + 3, seed=7)
    assert [s.provenance.epoch for s in corpus[strata_count:]] == [1, 1, 1]


def test_provenance_is_complete():
    sampler = _sampler()
    sketch = sampler.sample(1, seed=99)[0]
    assert sketch.provenance.taxonomy_version == "0.1.0"
    assert sketch.provenance.seed == 99
    assert sketch.sketch_id.startswith("sk-")


def test_compliance_and_integration_expectations():
    sampler = _sampler()
    for sketch in sampler.sample(40, seed=5):
        kinds = {r.kind for r in sketch.expected_requirements}
        if sketch.assignment.compliance_regime == "none":
            assert RequirementKind.COMPLIANCE not in kinds
        else:
            assert RequirementKind.COMPLIANCE in kinds
        if sketch.assignment.integration_pattern == "none":
            assert RequirementKind.INTEGRATION not in kinds


def test_defect_rates_bounds():
    none_sampler = _sampler(contradiction=0.0, missing_must=0.0, ambiguity=0.0)
    assert all(s.planted_defects == [] for s in none_sampler.sample(30, seed=3))

    full_sampler = _sampler(contradiction=1.0, missing_must=1.0, ambiguity=1.0)
    for sketch in full_sampler.sample(30, seed=3):
        kinds = {d.kind.value for d in sketch.planted_defects}
        assert kinds == {"contradiction", "missing_must", "ambiguity"}
        refs = set(sketch.requirement_refs())
        caps = set(sketch.expected_capabilities)
        for defect in sketch.planted_defects:
            targets = defect.target_ref.split(" x ")
            if defect.kind is PlantedDefectKind.AMBIGUITY:
                assert all(t in caps for t in targets)
            else:
                assert all(t in refs for t in targets)
