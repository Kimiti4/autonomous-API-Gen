from app.engine.repository_code_scan import scan_repository

def test_scan_is_deterministic_and_finds_bug_risk_and_jagged_code():
    files=[("a.py","def f():\n    try:\n        x()\n    except:\n        pass  # stub\n")]
    a=scan_repository(files); b=scan_repository(files)
    assert a.digest==b.digest
    assert {f.rule for f in a.findings}=={"bare-except","stub-pass"}

def test_scan_is_sorted_and_never_executes_source():
    files=[("z.py","TODO"),("a.py","FIXME")]
    s=scan_repository(files)
    assert s.files_scanned==2
    assert [f.path for f in s.findings]==["a.py","z.py"]
    assert all(f.repairable for f in s.findings)
