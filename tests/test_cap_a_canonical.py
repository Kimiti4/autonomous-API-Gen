from tiannara.domain.services.canonical import canonical_hash, canonical_json


def test_canonical_json_key_order_independent():
    a = {"x": 1, "y": {"b": 2, "a": 1}}
    b = {"y": {"a": 1, "b": 2}, "x": 1}
    assert canonical_json(a) == canonical_json(b)
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_json_list_order_is_semantic():
    assert canonical_json([1, 2]) != canonical_json([2, 1])


def test_canonical_hash_is_sha256_hex():
    h = canonical_hash("hello")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
