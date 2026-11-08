"""Tier B canonicalization contracts F-04 / F-05."""

from __future__ import annotations

import hashlib

from certification.payroll.candidate_fixture import payroll_isr_revision
from compiler.core.canonical_api_contract import build_canonical_api_contract, contract_digest
from compiler.core.contract_canonicalization import canonical_bytes_f05
from compiler.core.lowering import isr_to_plan
from compiler.core.plan_canonicalization import canonical_bytes_f04
from isr.core.canonicalization_registry import F04_COMPILATION_PLAN, F05_API_CONTRACT, get_canonicalization_contract


def test_f04_contract_registered():
    c = get_canonicalization_contract(F04_COMPILATION_PLAN.isr_family_id)
    assert c.canonicalization_version == "1.0.0"


def test_f05_contract_registered():
    c = get_canonicalization_contract(F05_API_CONTRACT.isr_family_id)
    assert c.hash_algorithm == "sha256"


def test_plan_and_contract_bytes_stable_on_payroll():
    rev = payroll_isr_revision()
    plan = isr_to_plan(rev)
    b1 = canonical_bytes_f04(plan)
    b2 = canonical_bytes_f04(plan)
    assert b1 == b2
    contract = build_canonical_api_contract(plan)
    dig = hashlib.sha256(canonical_bytes_f05(contract)).hexdigest()
    assert dig == contract_digest(contract)
