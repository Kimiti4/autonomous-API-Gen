from app.engine.quality_evaluation import (
    QUALITY_DIMENSIONS, build_quality_criteria, assess_quality, aggregate_quality
)

def test_quality_dimensions_are_explicit():
    assert "security" in QUALITY_DIMENSIONS
    assert "accessibility" in QUALITY_DIMENSIONS
    assert "operability" in QUALITY_DIMENSIONS

def test_requirements_drive_quality_criteria():
    c=build_quality_criteria({"security":("SEC-1",),"performance":("PERF-1",)})
    assert [x.dimension for x in c]==["security","performance"]
    assert c[0].requirement_ids==("SEC-1",)

def test_missing_requirement_is_inconclusive():
    c=build_quality_criteria({"security":("SEC-1",)})[0]
    a=assess_quality("A",c,(),("e1",))
    assert a.status=="INCONCLUSIVE"
    assert a.unresolved==("SEC-1",)

def test_evidence_required_for_supported_quality():
    c=build_quality_criteria({"security":("SEC-1",)})[0]
    assert assess_quality("A",c,("SEC-1",),("e1",)).status=="SUPPORTED"
    assert assess_quality("A",c,("SEC-1",),()).status=="INCONCLUSIVE"

def test_aggregate_fails_closed_to_inconclusive():
    c=build_quality_criteria({"security":("SEC-1",)})[0]
    a=assess_quality("A",c,("SEC-1",),())
    assert aggregate_quality((a,))=="INCONCLUSIVE"
