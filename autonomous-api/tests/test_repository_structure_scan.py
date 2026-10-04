from app.engine.repository_structure_scan import analyze_repository_structure

def test_structure_scan_extracts_imports_and_finds_structural_risks():
    scan=analyze_repository_structure([
        ("a.py","import missing_mod\nif False:\n    x=1\n"),
        ("b.py","x = 1\n"),
    ])
    assert ("a.py","missing_mod") in scan.imports
    assert {f.rule for f in scan.findings}=={"unresolved-local-import","dead-branch"}

def test_structure_scan_is_deterministic():
    files=[("b.py","x=1"),("a.py","import os")]
    assert analyze_repository_structure(files).digest==analyze_repository_structure(tuple(reversed(files))).digest
