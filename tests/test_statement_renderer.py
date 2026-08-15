from pathlib import Path

from tiannara.application.synthesis.personas import load_persona_pool, select_persona
from tiannara.application.synthesis.render_planner import (
    build_render_plan,
    measure_defect_rates,
)
from tiannara.application.synthesis.sampler import DefectRates, StratifiedSampler
from tiannara.application.synthesis.statement_renderer import (
    RenderConfig,
    StatementRenderer,
    build_render_request,
)
from tiannara.application.synthesis.taxonomy import StratificationTaxonomy
from tiannara.domain.models.model_call import (
    ModelCallRecord,
    ModelCallStatus,
    compute_call_signature,
    hash_payload,
)
from tiannara.domain.models.requirement_sketch import PlantedDefectKind, RequirementSketch
from tiannara.infrastructure.llm.recorded_provider import RecordedModelProvider
from tiannara.infrastructure.llm.transcript import ModelCallTranscript

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY_PATH = ROOT / "config" / "taxonomy" / "v0.1.yaml"
PERSONAS_PATH = ROOT / "config" / "personas" / "v0.1.yaml"


def _sampler(rates: DefectRates) -> StratifiedSampler:
    return StratifiedSampler(StratificationTaxonomy.load(TAXONOMY_PATH), rates)


def _full_defect_sketch() -> RequirementSketch:
    sampler = _sampler(DefectRates(contradiction=1.0, missing_must=1.0, ambiguity=1.0))
    return sampler.sample(1, seed=11)[0]


def test_persona_pool_loads_and_selects_deterministically():
    pool = load_persona_pool(PERSONAS_PATH)
    assert len(pool.personas) == 5
    sketch = _sampler(DefectRates()).sample(1, seed=3)[0]
    assert select_persona(pool, sketch).id == select_persona(pool, sketch).id


def test_render_plan_materializes_defects_and_guards_leakage():
    sketch = _full_defect_sketch()
    pool = load_persona_pool(PERSONAS_PATH)
    persona = select_persona(pool, sketch)
    plan = build_render_plan(sketch, persona)

    kinds = {d.kind for d in sketch.planted_defects}
    assert kinds == {
        PlantedDefectKind.CONTRADICTION,
        PlantedDefectKind.MISSING_MUST,
        PlantedDefectKind.AMBIGUITY,
    }

    assert plan.omitted_refs, "expected an omitted requirement"
    mentioned_topics = {m.topic for m in plan.mentions}
    ref_to_topic = {r.ref_id: r.topic for r in sketch.expected_requirements}
    for omitted in plan.omitted_refs:
        assert ref_to_topic[omitted] not in mentioned_topics

    assert plan.contradictions, "expected a contradiction pair"
    assert plan.ambiguities, "expected an ambiguous capability"

    payload = plan.prompt_payload()
    assert "omitted_refs" not in payload


def test_render_request_is_deterministic():
    sketch = _full_defect_sketch()
    pool = load_persona_pool(PERSONAS_PATH)
    persona = select_persona(pool, sketch)
    plan = build_render_plan(sketch, persona)
    req_a = build_render_request(plan, RenderConfig())
    req_b = build_render_request(plan, RenderConfig())
    assert compute_call_signature(req_a) == compute_call_signature(req_b)


def _seed_render_fixture(tmp_path, sketch, persona, statement_text):
    plan = build_render_plan(sketch, persona)
    request = build_render_request(plan, RenderConfig())
    transcript = ModelCallTranscript(tmp_path / "render.jsonl")
    payload = {"statement": statement_text}
    transcript.append(
        ModelCallRecord(
            signature_hash=compute_call_signature(request),
            model_id=request.model_id,
            task=request.task,
            output_schema_id=request.output_schema_id,
            output_payload=payload,
            response_hash=hash_payload(payload),
            decoding=request.decoding,
        )
    )
    return transcript, request


def test_renderer_replay_pairs_statement_with_ground_truth(tmp_path):
    sketch = _full_defect_sketch()
    pool = load_persona_pool(PERSONAS_PATH)
    persona = select_persona(pool, sketch)
    transcript, _request = _seed_render_fixture(
        tmp_path, sketch, persona, "We need a way to manage marina berths reliably."
    )
    renderer = StatementRenderer(RecordedModelProvider(transcript))
    instance = renderer.render(sketch, persona)

    assert instance.statement == "We need a way to manage marina berths reliably."
    assert instance.persona_id == persona.id
    assert instance.sketch.sketch_id == sketch.sketch_id
    assert instance.render_record.status is ModelCallStatus.REPLAYED


def test_defect_rate_measurement_matches_configuration():
    sampler = _sampler(DefectRates(contradiction=0.5, missing_must=0.0, ambiguity=0.0))
    sketches = sampler.sample(200, seed=21)
    rates = measure_defect_rates(sketches)
    assert abs(rates["contradiction"] - 0.5) <= 0.15
    assert rates["missing_must"] == 0.0
    assert rates["ambiguity"] == 0.0


def test_render_corpus_is_deterministic(tmp_path):
    sampler = _sampler(DefectRates())
    sketches = sampler.sample(5, seed=31)
    pool = load_persona_pool(PERSONAS_PATH)
    config = RenderConfig()

    transcript = ModelCallTranscript(tmp_path / "corpus.jsonl")
    expected_statements = {}
    for sketch in sketches:
        persona = select_persona(pool, sketch)
        plan = build_render_plan(sketch, persona)
        request = build_render_request(plan, config)
        statement_text = f"statement for {sketch.sketch_id}"
        expected_statements[sketch.sketch_id] = statement_text
        payload = {"statement": statement_text}
        transcript.append(
            ModelCallRecord(
                signature_hash=compute_call_signature(request),
                model_id=request.model_id,
                task=request.task,
                output_schema_id=request.output_schema_id,
                output_payload=payload,
                response_hash=hash_payload(payload),
                decoding=request.decoding,
            )
        )

    renderer = StatementRenderer(RecordedModelProvider(transcript), config)
    first = {i.sketch_id: i.statement for i in renderer.render_corpus(sketches, pool)}
    second = {i.sketch_id: i.statement for i in renderer.render_corpus(sketches, pool)}
    assert first == second
    assert first == expected_statements
