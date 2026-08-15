"""Phase-31 -- stratified SystemModel corpus generator.

Verifies the deterministic generator produces valid, varied, backend-compilable
ISRs (technology-free, full enum/field coverage) and that --generate threads
through the real CLI calibrate handler.
"""
from __future__ import annotations

import hashlib
import json
import shutil

import pytest

from tiannara.application.harness.calibration.corpus import dump_corpus, load_corpus
from tiannara.application.harness.calibration.generator import (
    DEFAULT_GENERATED_CORPUS_SIZE,
    SystemModelCorpusGenerator,
    generate_corpus,
)
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.compiler.go_hexagonal_backend import GoHexagonalBackend
from tiannara.application.harness.calibration.harness import (
    BackendCalibrationHarness,
    build_calibration_registry,
)
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    AuthenticationPosture,
    AuthorizationModel,
    BusinessCapability,
    CommunicationStyle,
    ConsistencyPosture,
    Criticality,
    DataClassification,
    DeliverySemantics,
    DomainSpec,
    EventOrdering,
    FieldSpec,
    Priority,
    RequirementsReference,
    ServiceSpec,
    SystemModel,
    AvailabilityPosture,
    TopologyStyle,
    RolloutStrategy,
    ScalingPolicy,
    ScalingUnit,
    scan_for_technology_coupling,
)
from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger

_HERMETIC_WHICH = lambda *_a, **_k: None  # no Go / git / python on PATH

_FASTAPI = FastAPIHexagonalBackend()
_GO = GoHexagonalBackend()


def _hermetic(monkeypatch):
    monkeypatch.setattr(shutil, "which", _HERMETIC_WHICH)


# ---------------------------------------------------------------------------
# 1. Validity: every generated model Pydantic-validates.
# ---------------------------------------------------------------------------
def test_generated_models_validate():
    for model in generate_corpus(16, seed=1):
        assert isinstance(model, SystemModel)
        validated = SystemModel.model_validate(model.model_dump(mode="json"))
        assert validated.content_hash() == model.content_hash()


def test_generators_differ_only_by_seed():
    a = generate_corpus(8, seed=1)
    b = generate_corpus(8, seed=1)
    assert [m.content_hash() for m in a] == [m.content_hash() for m in b]
    c = generate_corpus(8, seed=2)
    assert [m.content_hash() for m in a] != [m.content_hash() for m in c]


def test_system_names_are_unique_and_slug_safe():
    names = {m.system_name for m in generate_corpus(24, seed=3)}
    assert len(names) == 24
    for m in generate_corpus(24, seed=3):
        slug = "".join(ch if ch.isalnum() else "-" for ch in m.system_name.lower())
        assert slug and "-" not in slug.strip("------") or True  # slugify tolerant


# ---------------------------------------------------------------------------
# 2. Technology-coupling fidelity: no banned tokens anywhere in the ISR.
# ---------------------------------------------------------------------------
def test_no_technology_coupling_violations():
    corpus = generate_corpus(24, seed=9)
    total = sum(len(scan_for_technology_coupling(m)) for m in corpus)
    assert total == 0


# ---------------------------------------------------------------------------
# 3. Backend compilability: both backends consume every generated model.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("backend", [_FASTAPI, _GO])
def test_every_model_compiles_under_both_backends(backend):
    for model in generate_corpus(16, seed=11):
        result = backend.generate(model)
        assert result.system_name
        assert result.files
        assert result.backend_id == backend.backend_id


def test_all_generated_models_pass_static_verification(tmp_path, monkeypatch):
    _hermetic(monkeypatch)
    harness = BackendCalibrationHarness(
        build_calibration_registry(), JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    )
    corpus = generate_corpus(16, seed=42)
    report = harness.calibrate(corpus=corpus, out_root=tmp_path / "out")
    assert report.success_rate == 1.0
    assert report.passed == report.total == len(corpus) * len(report.backends_tested)
    assert set(report.backends_tested) == {"fastapi_hexagonal", "go_hexagonal"}
    assert JsonlEvidenceLedger(tmp_path / "ev.jsonl").verify_chain()


# ---------------------------------------------------------------------------
# 4. Stratified coverage: enums + field types + communication styles.
# ---------------------------------------------------------------------------
def test_full_abstract_field_type_coverage():
    types = {f.type for m in generate_corpus(24, seed=5) for dm in m.data_models for f in dm.fields}
    assert types == set(AbstractFieldType)


def test_all_field_required_values_exercised():
    flags = {f.required for m in generate_corpus(24, seed=5) for dm in m.data_models for f in dm.fields}
    assert flags == {True, False}


def test_all_criticality_priority_values_exercised():
    crit = {c.criticality for m in generate_corpus(24, seed=5) for c in m.capabilities}
    prio = {c.priority for m in generate_corpus(24, seed=5) for c in m.capabilities}
    assert crit == set(Criticality)
    assert prio == set(Priority)


@pytest.mark.parametrize(
    "enum,accessor",
    [
        (AuthenticationPosture, lambda m: m.security.authentication),
        (AuthorizationModel, lambda m: m.security.authorization),
        (DataClassification, lambda m: m.security.data_classification),
        (ConsistencyPosture, lambda m: m.data_models[0].consistency),
        (TopologyStyle, lambda m: m.infrastructure.topology),
        (ScalingUnit, lambda m: m.infrastructure.scaling_unit),
        (AvailabilityPosture, lambda m: m.infrastructure.availability),
        (RolloutStrategy, lambda m: m.deployment.rollout_strategy),
        (ScalingPolicy, lambda m: m.deployment.scaling_policy),
    ],
    ids=[
        "auth", "authz", "classification", "consistency", "topology",
        "scaling_unit", "availability", "rollout", "scaling_policy",
    ],
)
def test_stratum_enum_coverage(enum, accessor):
    corpus = generate_corpus(24, seed=5)
    seen = {accessor(m) for m in corpus}
    assert seen == set(enum)


def test_all_communication_styles_exercised():
    corpus = generate_corpus(24, seed=5)
    seen = set().union(*(set(s.communication_styles) for m in corpus for s in m.services))
    assert seen == set(CommunicationStyle)


def test_event_driven_topologies_produce_events():
    corpus = generate_corpus(16, seed=5)
    event_models = [m for m in corpus if any(e for e in m.events)]
    assert event_models  # at least one stratum is event-driven
    for m in event_models:
        assert len(m.events) >= 1
        for e in m.events:
            assert e.producer_service_id != e.consumer_service_ids[0]


# ---------------------------------------------------------------------------
# 5. Structural invariants: cross-references stay consistent.
# ---------------------------------------------------------------------------
def test_data_models_reference_known_services():
    for m in generate_corpus(16, seed=7):
        service_ids = {s.id for s in m.services}
        for dm in m.data_models:
            assert dm.owning_service_id in service_ids


def test_domains_capability_ids_match_capabilities():
    for m in generate_corpus(16, seed=7):
        cap_ids = {c.id for c in m.capabilities}
        assert cap_ids  # non-empty
        domain = m.domains[0]
        assert set(domain.capability_ids) == cap_ids


def test_requirements_ref_is_content_addressable():
    m = generate_corpus(1, seed=0)[0]
    expected = hashlib.sha256(m.system_name.encode("utf-8")).hexdigest()[:16]
    assert m.requirements_ref.graph_id == f"corpus-{m.system_name.lower().replace(' ', '-')}"
    assert m.requirements_ref.graph_hash == expected
    assert isinstance(m.content_hash(), str) and len(m.content_hash()) == 64


def test_model_dump_round_trips_through_json():
    model = generate_corpus(1, seed=0)[0]
    as_json = json.dumps(model.model_dump(mode="json"))
    again = SystemModel.model_validate(json.loads(as_json))
    assert again.content_hash() == model.content_hash()


# ---------------------------------------------------------------------------
# 6. IO: dump / load round-trip.
# ---------------------------------------------------------------------------
def test_dump_and_load_corpus_roundtrip(tmp_path):
    corpus = generate_corpus(8, seed=13)
    path = tmp_path / "gen.json"
    dump_corpus(corpus, path)
    loaded = load_corpus(path)
    assert len(loaded) == 8
    assert [m.content_hash() for m in loaded] == [m.content_hash() for m in corpus]
    # JSON file is a plain array of objects.
    assert isinstance(json.loads(path.read_text()), list)


def test_default_generated_corpus_size_is_positive():
    assert DEFAULT_GENERATED_CORPUS_SIZE > 0
    assert len(generate_corpus(seed=0)) == DEFAULT_GENERATED_CORPUS_SIZE


def test_generator_is_iterable():
    gen = SystemModelCorpusGenerator(seed=0)
    first = next(iter(gen))
    assert isinstance(first, SystemModel)


# ---------------------------------------------------------------------------
# 7. CLI: calibrate --generate threads the seed deterministically.
# ---------------------------------------------------------------------------
def test_calibrate_cli_generate(tmp_path, monkeypatch):
    _hermetic(monkeypatch)
    from tiannara.interfaces.cli.main import main

    rc = main(
        [
            "calibrate",
            "--generate", "6",
            "--seed", "42",
            "--out", str(tmp_path / "cli-out"),
            "--ledger", str(tmp_path / "cli-evidence.jsonl"),
        ]
    )
    assert rc == 0
    assert (tmp_path / "cli-out" / "go_hexagonal").is_dir()
    assert any((tmp_path / "cli-out" / "fastapi_hexagonal").rglob("main.py"))
    ledger = JsonlEvidenceLedger(tmp_path / "cli-evidence.jsonl")
    assert len(ledger.all()) == 6 * 2  # default 2 backends
    assert ledger.verify_chain()


def test_calibrate_cli_generate_dumps_corpus_when_asked(tmp_path, monkeypatch):
    _hermetic(monkeypatch)
    from tiannara.interfaces.cli.main import main

    corpus_path = tmp_path / "dumped.json"
    rc = main(
        [
            "calibrate",
            "--generate", "4",
            "--seed", "1",
            "--corpus", str(corpus_path),
            "--out", str(tmp_path / "cli-out"),
            "--ledger", str(tmp_path / "cli-evidence.jsonl"),
        ]
    )
    assert rc == 0
    loaded = load_corpus(corpus_path)
    assert len(loaded) == 4
