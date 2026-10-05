import pytest
from app.engine.certified_documentation import DocumentationSection,build_documentation_manifest,validate_documentation_manifest

def sec():
 return DocumentationSection("S","Authentication","Users can sign in",("E1",),("R1",))
def test_documentation_requires_certification_and_provenance():
 m=build_documentation_manifest(project_id="P",certification_digest="D",sections=(sec(),),certified=True)
 assert not validate_documentation_manifest(m,{"E1"},{"R1"})
def test_uncertified_documentation_fails():
 with pytest.raises(ValueError): build_documentation_manifest(project_id="P",certification_digest="D",sections=(sec(),),certified=False)
def test_missing_evidence_fails():
 with pytest.raises(ValueError): build_documentation_manifest(project_id="P",certification_digest="D",sections=(DocumentationSection("S","x","content",(),("R1",)),),certified=True)
