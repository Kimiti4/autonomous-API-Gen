from tiannara.domain.models.model_call import (
    DecodingParameters,
    ModelCallRecord,
    StructuredCompletionRequest,
    compute_call_signature,
)


def _request(prompt: str = "Extract the requirement graph.") -> StructuredCompletionRequest:
    return StructuredCompletionRequest(
        model_id="stub@1",
        task="extraction",
        prompt=prompt,
        output_schema_id="requirement_graph.v1",
    )


def test_signature_is_deterministic():
    assert compute_call_signature(_request()) == compute_call_signature(_request())


def test_signature_is_prompt_sensitive():
    assert compute_call_signature(_request("a")) != compute_call_signature(_request("b"))


def test_signature_is_decoding_sensitive():
    base = _request()
    hotter = base.model_copy(update={"decoding": DecodingParameters(temperature=0.7)})
    assert compute_call_signature(base) != compute_call_signature(hotter)


def test_signature_is_model_sensitive():
    base = _request()
    other = base.model_copy(update={"model_id": "stub@2"})
    assert compute_call_signature(base) != compute_call_signature(other)


def test_provenance_tag_format():
    sig = compute_call_signature(_request())
    record = ModelCallRecord(signature_hash=sig, model_id="stub@1")
    assert record.provenance_tag() == f"stub@1:{sig}"
