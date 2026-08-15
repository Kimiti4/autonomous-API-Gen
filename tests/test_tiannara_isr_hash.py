from tiannara.domain.models.isr import (
    IntermediateSoftwareRepresentation as ISR,
    IntentSpecification,
)


def _isr():
    return ISR(
        system_id="s1",
        system_name="demo",
        intent=IntentSpecification(statement="a service", domain="general"),
        lineage=["intent:s1", "genome:g1"],
    )


def test_content_hash_excludes_lineage():
    a = _isr()
    b = _isr()
    b.lineage = []
    assert a.content_hash() == b.content_hash()


def test_content_hash_changes_when_content_changes():
    a = _isr()
    b = _isr()
    b.system_name = "changed"
    assert a.content_hash() != b.content_hash()


def test_content_hash_is_stable():
    a = _isr()
    assert a.content_hash() == a.content_hash()
