#!/usr/bin/env python3
import os, re, sys
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
sys.path.insert(0, os.path.join(_root, "autonomous-api"))
sys.path.insert(0, _here)
from extract_contract_schema import collect_models
PARITY = {
    "EvolutionEventEnvelope":     ("observation-client/src/contracts/envelope.ts", "EvolutionEventEnvelope"),
    "EventSource":                ("observation-client/src/contracts/envelope.ts", "EventSource"),
    "EventIntegrity":             ("observation-client/src/contracts/envelope.ts", "EventIntegrity"),
    "ErrorEnvelope":              ("observation-client/src/contracts/errors.ts", "ErrorEnvelope"),
    "ObservationError":           ("observation-client/src/contracts/errors.ts", "ObservationError"),
    "RecoveryGuidance":           ("observation-client/src/contracts/errors.ts", "RecoveryGuidance"),
    "ContractMetadata":           ("observation-client/src/contracts/provenance.ts", "ContractMetadata"),
    "ObservationProvenance":      ("observation-client/src/contracts/provenance.ts", "ObservationProvenance"),
    "ObservationSnapshotWrapper": ("observation-client/src/contracts/observations.ts", "ObservationSnapshotWrapper"),
    "CapabilityContract":         ("observation-client/src/contracts/observations.ts", "CapabilityContract"),
    "GovernanceProjection":       ("observation-client/src/contracts/governance.ts", "GovernanceProjection"),
    "GovernanceDecision":         ("observation-client/src/contracts/governance.ts", "GovernanceDecision"),
    "CandidateLineage":           ("observation-client/src/contracts/lineage.ts", "CandidateLineage"),
}
def parse_ts_interfaces(path):
    text = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"interface\s+(\w+)[^{]*\{(.*?)\n\}", text, re.DOTALL):
        name, body = m.group(1), m.group(2)
        fields = set()
        for line in body.splitlines():
            fm = re.match(r"\s*(?:readonly\s+)?(\w+)\??:", line)
            if fm: fields.add(fm.group(1))
        out[name] = fields
    return out
def main():
    pyf = {n: set(m.model_fields.keys()) for n, m in collect_models().items()}
    ts_cache, failures = {}, []
    for py_model, (ts_rel, ts_iface) in PARITY.items():
        if py_model not in pyf:
            failures.append(f"{py_model}: not found in Python contracts"); continue
        ts_abs = os.path.join(_root, ts_rel)
        if ts_abs not in ts_cache:
            if not os.path.isfile(ts_abs):
                failures.append(f"{ts_rel}: not found"); continue
            ts_cache[ts_abs] = parse_ts_interfaces(ts_abs)
        ts_fields = ts_cache[ts_abs].get(ts_iface)
        if ts_fields is None:
            failures.append(f"{ts_iface}: not found in {ts_rel}"); continue
        p, t = pyf[py_model], ts_fields
        if p != t:
            failures.append(f"{py_model}<->{ts_iface}: py-only={sorted(p-t)} ts-only={sorted(t-p)}")
    if failures:
        print("CONTRACT PARITY VIOLATIONS:", file=sys.stderr)
        for f in failures: print("  " + f, file=sys.stderr)
        return 1
    print(f"contract parity OK across {len(PARITY)} mapped contracts")
    return 0
if __name__ == "__main__": sys.exit(main())
