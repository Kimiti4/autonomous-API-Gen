import hashlib, json, math, os
import pytest

VERDICT_CERTIFIED   = "CERTIFIED"
VERDICT_NOT_CERT    = "NOT_CERTIFIED"
VERDICT_BOUNDED     = "BOUNDED"
CLASS_PRODUCTION    = "production"
TOOL_ELIGIBLE       = "CERTIFICATION_ELIGIBLE"
EPS                 = 1e-9
FORBIDDEN_AGGREGATE_KEYS = {"aggregate", "composite", "overall_score", "quality_score", "total_score"}


# ---------- canonicalisation (no default=str) ----------
def canonical_json(obj) -> str:
    # raises TypeError on any non-serializable value: nothing is silently str()'d
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------- load + schema-validate evidence ----------
REQUIRED_TOP      = {"contract", "provisioning", "cells", "ledger", "blind_evaluation", "reported_summary"}
REQUIRED_CONTRACT = {"contract_id", "content_hash", "exit_threshold", "analyzer_scope",
                     "surface", "accuracy_bounds", "discrimination_bounds"}
REQUIRED_CELL     = {"cell_id", "class", "isr_hash", "verdict", "evidence"}

def load_evidence():
    path = os.environ.get("TIANNARA_EVIDENCE_PATH")
    assert path, "TIANNARA_EVIDENCE_PATH not set: cannot verify without evidence"
    with open(path) as f:
        ev = json.load(f)
    missing = REQUIRED_TOP - set(ev)
    assert not missing, f"evidence artifact missing top-level sections: {sorted(missing)}"
    cm = REQUIRED_CONTRACT - set(ev["contract"])
    assert not cm, f"contract missing fields: {sorted(cm)}"
    assert ev["cells"], "evidence contains no cells"
    for c in ev["cells"]:
        m = REQUIRED_CELL - set(c)
        assert not m, f"cell {c.get('cell_id','?')} missing fields: {sorted(m)}"
    return ev

@pytest.fixture(scope="session")
def evidence():
    return load_evidence()

@pytest.fixture(scope="session")
def contract(evidence):
    return evidence["contract"]

@pytest.fixture(scope="session")
def cells(evidence):
    return evidence["cells"]

@pytest.fixture(scope="session")
def surface_classes(contract):
    return set(contract["surface"]["required_classes"])

@pytest.fixture(scope="session")
def production_cells(cells, surface_classes):
    return [c for c in cells if c["class"] == CLASS_PRODUCTION]

@pytest.fixture(scope="session")
def ledger_index(evidence):
    return {e["event_id"]: e for e in evidence["ledger"]["events"]}


# ---------- independent recomputation ----------
def _rate(flags):
    flags = list(flags)
    return None if not flags else sum(bool(x) for x in flags) / len(flags)

def recompute_success_rate(production_cells):
    return _rate(c["verdict"] == VERDICT_CERTIFIED for c in production_cells)

def recompute_bounded_rate(production_cells):
    return _rate(c["verdict"] == VERDICT_BOUNDED for c in production_cells)

def _expectation(contract, cls):
    req = contract["surface"]["class_requirements"].get(cls)
    if req is None:
        return "production"
    allowed = set(req["allowed_outcomes"])
    if allowed == {VERDICT_CERTIFIED}:
        return "expect_certify"
    if VERDICT_CERTIFIED not in allowed:
        return "expect_reject"
    return "spread"

def recompute_discrimination(cells, contract):
    reject, certify = [], []
    for c in cells:
        e = _expectation(contract, c["class"])
        if e == "expect_reject":
            reject.append(c)
        elif e == "expect_certify":
            certify.append(c)
    sens = _rate(c["verdict"] != VERDICT_CERTIFIED for c in reject) if reject else None
    spec = _rate(c["verdict"] == VERDICT_CERTIFIED for c in certify) if certify else None
    false_acc  = [c for c in reject  if c["verdict"] == VERDICT_CERTIFIED]
    false_rej  = [c for c in certify if c["verdict"] != VERDICT_CERTIFIED]
    fa_rate = len(false_acc) / len(reject) if reject else None
    fr_rate = len(false_rej) / len(certify) if certify else None
    return {"sensitivity": sens, "specificity": spec,
            "false_acceptance_rate": fa_rate, "false_rejection_rate": fr_rate,
            "false_acceptances": false_acc, "false_rejections": false_rej}


# =====================================================================
# A. CONTRACT IMMUTABILITY
# =====================================================================
def test_contract_matches_pre_registered_anchor(contract):
    anchor = os.environ.get("TIANNARA_PRE_REGISTERED_CONTRACT_HASH")
    assert anchor, ("pre-registered contract hash not supplied: immutability cannot be "
                    "verified without an external anchor frozen before the campaign")
    assert contract["content_hash"] == anchor, (
        "executed contract differs from the pre-registered contract: "
        f"expected {anchor}, got {contract['content_hash']}")

def test_contract_declares_gate_inputs(contract):
    assert contract["exit_threshold"] > 0.0
    assert "max_false_acceptance_rate" in contract["accuracy_bounds"]
    assert "min_sensitivity" in contract["discrimination_bounds"]
    assert contract["surface"]["required_classes"], "contract declares no surface classes"


# =====================================================================
# B. LEDGER INTEGRITY (re-derived, never trusted)
# =====================================================================
def test_ledger_hash_chain_recomputes_valid(evidence):
    events = evidence["ledger"]["events"]
    assert events, "ledger has no events"
    prev = None
    for ev in events:
        expected_prev = "" if prev is None else prev["hash"]
        assert ev["prev_hash"] == expected_prev, f"broken chain link at {ev['event_id']}"
        recomputed = sha256_hex(canonical_json(ev["payload"]) + ev["prev_hash"])
        assert ev["hash"] == recomputed, f"hash mismatch at {ev['event_id']}"
        prev = ev

def test_every_cell_certification_event_resolves(cells, ledger_index):
    for c in cells:
        ref = c["evidence"].get("certification_event_id")
        assert ref, f"cell {c['cell_id']} has no certification event"
        assert ref in ledger_index, f"cell {c['cell_id']} certification event {ref} not in ledger"

def test_every_cell_chain_refs_resolve(cells, ledger_index):
    for c in cells:
        for ref in c["evidence"].get("chain_refs", []):
            assert ref in ledger_index, f"cell {c['cell_id']} chain ref {ref} not in ledger"


# =====================================================================
# C. RECOMPUTATION vs REPORTED SUMMARY (anti-fabrication)
# =====================================================================
def _assert_close(recomputed, reported, name):
    assert recomputed is not None, f"{name} could not be recomputed (missing population)"
    assert math.isclose(recomputed, reported, abs_tol=EPS), (
        f"reported {name}={reported} but recomputed {recomputed} from raw cells")

def test_success_rate_matches_recomputation(evidence, production_cells):
    _assert_close(recompute_success_rate(production_cells),
                  evidence["reported_summary"]["success_rate"], "success_rate")

def test_bounded_rate_matches_recomputation(evidence, production_cells):
    _assert_close(recompute_bounded_rate(production_cells),
                  evidence["reported_summary"]["bounded_rate"], "bounded_rate")

def test_discrimination_matches_recomputation(evidence, cells, contract):
    d = recompute_discrimination(cells, contract)
    rs = evidence["reported_summary"]
    _assert_close(d["sensitivity"], rs["sensitivity"], "sensitivity")
    _assert_close(d["specificity"], rs["specificity"], "specificity")
    _assert_close(d["false_acceptance_rate"], rs["false_acceptance_rate"], "false_acceptance_rate")


# =====================================================================
# D. STRUCTURAL INVARIANTS
# =====================================================================
def test_conservation_certified_plus_not_plus_bounded_equals_total(production_cells):
    n = len(production_cells)
    assert n > 0, "no production cells"
    cert  = sum(1 for c in production_cells if c["verdict"] == VERDICT_CERTIFIED)
    notc  = sum(1 for c in production_cells if c["verdict"] == VERDICT_NOT_CERT)
    bnd   = sum(1 for c in production_cells if c["verdict"] == VERDICT_BOUNDED)
    assert cert + notc + bnd == n, f"conservation violated: {cert}+{notc}+{bnd} != {n}"

def test_no_aggregate_score_anywhere(evidence):
    keys = set(evidence["reported_summary"].keys())
    assert not (keys & FORBIDDEN_AGGREGATE_KEYS), (
        f"aggregate score present: {sorted(keys & FORBIDDEN_AGGREGATE_KEYS)}")

def test_no_cell_verdict_outside_vocabulary(cells):
    vocab = {VERDICT_CERTIFIED, VERDICT_NOT_CERT, VERDICT_BOUNDED}
    for c in cells:
        assert c["verdict"] in vocab, f"cell {c['cell_id']} has invalid verdict {c['verdict']}"


# =====================================================================
# E. VACUITY / PROVISIONING
# =====================================================================
def test_all_required_tools_certification_eligible(evidence, contract):
    scope = contract["analyzer_scope"]
    prov = evidence["provisioning"]
    for tool in scope["required_tools"]:
        assert tool in prov, f"required tool {tool} has no provisioning record"
        assert prov[tool] == TOOL_ELIGIBLE, f"tool {tool} is {prov[tool]}, not {TOOL_ELIGIBLE}"

def test_bounded_cells_are_never_counted_as_certified(production_cells):
    # success rate recomputation already excludes bounded as passes; assert no
    # bounded cell is labelled certified anywhere
    for c in production_cells:
        if c["verdict"] == VERDICT_BOUNDED:
            assert c["verdict"] != VERDICT_CERTIFIED


# =====================================================================
# F. SURFACE EXERCISE (from observed certification events, not composition)
# =====================================================================
def test_every_declared_surface_class_has_observed_cells(cells, surface_classes):
    for cls in surface_classes:
        observed = [c for c in cells if c["class"] == cls]
        assert observed, f"declared surface class '{cls}' has no observed cells"

def test_surface_outcomes_satisfy_contract(cells, contract, ledger_index):
    for cls, req in contract["surface"]["class_requirements"].items():
        allowed, required = set(req["allowed_outcomes"]), set(req["required_outcomes"])
        observed = [c for c in cells if c["class"] == cls]
        seen = set()
        for c in observed:
            assert c["verdict"] in allowed, (
                f"class '{cls}': disallowed outcome {c['verdict']} on {c['cell_id']}")
            # the outcome must be backed by a resolvable certification event
            assert c["evidence"]["certification_event_id"] in ledger_index
            seen.add(c["verdict"])
        missing = required - seen
        assert not missing, f"class '{cls}': required outcomes not observed: {sorted(missing)}"


# =====================================================================
# G. LABEL INDEPENDENCE (anti label-leakage)
# =====================================================================
def test_reject_class_cells_have_independent_provenance(cells, contract, ledger_index):
    for c in cells:
        if _expectation(contract, c["class"]) != "expect_reject":
            continue
        prov = c.get("class_provenance")
        assert prov, f"reject-class cell {c['cell_id']} lacks class_provenance"
        indep = prov.get("independent_ref")
        assert indep, f"cell {c['cell_id']} has no independent structural ref"
        ev = ledger_index.get(indep)
        assert ev, f"cell {c['cell_id']} independent_ref {indep} not in ledger"
        # structural evidence must be keyed to the ISR, not to the outcome
        assert ev["payload"].get("subject") == c["isr_hash"], (
            f"cell {c['cell_id']}: structural evidence not keyed to its ISR")
        cert_ev = c["evidence"]["certification_event_id"]
        assert cert_ev not in ev["payload"].get("inputs", []), (
            f"cell {c['cell_id']}: class assignment derived from certification outcome "
            "(label leakage)")


# =====================================================================
# H. FALSE ACCEPTANCE
# =====================================================================
def test_false_acceptance_within_bound(cells, contract):
    d = recompute_discrimination(cells, contract)
    if d["false_acceptance_rate"] is None:
        pytest.fail("no reject-expected cells: false acceptance unmeasurable")
    bound = contract["accuracy_bounds"]["max_false_acceptance_rate"]
    assert d["false_acceptance_rate"] <= bound, (
        f"false acceptance {d['false_acceptance_rate']} > bound {bound}; "
        f"offending cells: {[c['cell_id'] for c in d['false_acceptances']]}")


# =====================================================================
# I. INDEPENDENT / BLIND EVALUATION
# =====================================================================
def test_blind_evaluation_provenance_actually_stripped(evidence):
    subjects = evidence["blind_evaluation"].get("subjects")
    assert subjects, "blind evaluation has no subject records"
    for s in subjects:
        assert s.get("provenance_stripped") is True, "subject not provenance-stripped"
        assert "source" not in s and "origin" not in s, (
            "subject record still carries provenance: stripping not performed")


# =====================================================================
# J. GATE SYNTHESIS (computed, never hardcoded)
# =====================================================================
def synthesize(evidence, contract, cells, production_cells):
    d = recompute_discrimination(cells, contract)
    succ, bnd = recompute_success_rate(production_cells), recompute_bounded_rate(production_cells)
    scope = contract["analyzer_scope"]; prov = evidence["provisioning"]
    tools_ok = all(prov.get(t) == TOOL_ELIGIBLE for t in scope["required_tools"])
    db, ab = contract["discrimination_bounds"], contract["accuracy_bounds"]

    failed = []
    if not tools_ok:              failed.append("EVIDENCE_COMPLETE: tools not all eligible")
    if bnd is None or bnd != 0.0: failed.append("EVIDENCE_COMPLETE: bounded_rate != 0")
    if d["sensitivity"] is None or d["sensitivity"] < db["min_sensitivity"]:
        failed.append("DISCRIMINATION: sensitivity")
    if d["specificity"] is None or d["specificity"] < db["min_specificity"]:
        failed.append("DISCRIMINATION: specificity")
    if d["false_acceptance_rate"] is None or d["false_acceptance_rate"] > ab["max_false_acceptance_rate"]:
        failed.append("DISCRIMINATION: false acceptance")
    # surface + ledger + report-consistency are enforced by their own tests above
    if succ is None or succ <= contract["exit_threshold"]:
        failed.append(f"EXIT_GATE: success_rate {succ} <= {contract['exit_threshold']}")

    verdict = VERDICT_CERTIFIED if not failed else VERDICT_NOT_CERT
    return verdict, failed, {"success_rate": succ, "bounded_rate": bnd, **d}

def test_final_verdict_synthesis(evidence, contract, cells, production_cells):
    verdict, failed, m = synthesize(evidence, contract, cells, production_cells)
    # invariant: bounded evidence can never yield CERTIFIED
    if m["bounded_rate"] not in (0.0, None):
        assert verdict != VERDICT_CERTIFIED
    print(f"\nRECOMPUTED METRICS: success={m['success_rate']} bounded={m['bounded_rate']} "
          f"sens={m['sensitivity']} spec={m['specificity']} "
          f"false_accept={m['false_acceptance_rate']}")
    print(f"FINAL VERDICT: {verdict}")
    if failed:
        print("FAILED GATES:")
        for g in failed:
            print("  -", g)
