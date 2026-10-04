import pytest
from app.engine.repository_code_scan import scan_repository
from app.engine.code_repair import plan_code_repairs

def test_unmapped_findings_are_not_given_guessed_repairs():
    scan=scan_repository([("a.py","TODO")])
    assert plan_code_repairs(scan,{})==()

def test_repair_plan_is_bounded_to_scanned_findings():
    scan=scan_repository([("a.py","TODO")])
    assert plan_code_repairs(scan,{ "not-a-finding": object() })==()
