import json

from tiannara.application.compiler.composition import build_compiler_registry
from tiannara.domain.models.system_model import RequirementsReference, SystemModel


def test_react_generation_uses_data_binding_and_behavioral_test():
    model = SystemModel(
        system_name='React "unsafe" <title>',
        problem_statement="test",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
    )
    generated = build_compiler_registry().backend("react_ts").generate(model)
    app = generated.files["src/App.tsx"]
    test = generated.files["src/App.test.tsx"]
    assert f"const title = {json.dumps(model.system_name, ensure_ascii=True)};" in app
    assert "<h1>{title}</h1>" in app
    assert "renderToStaticMarkup(<App />)" in test
    assert "expect(true).toBe(true)" not in test
