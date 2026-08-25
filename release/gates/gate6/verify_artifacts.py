#!/usr/bin/env python3
import hashlib, importlib.util, json, os, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
FIXTURE = os.path.join(REPO, "observation-client/tests/fixtures/reducer_vectors.json")
TEST_MODULE = os.path.join(REPO, "autonomous-api/tests/observation/test_reducer_equivalence.py")
sys.path.insert(0, os.path.join(REPO, "autonomous-api"))
def load_builder():
    spec = importlib.util.spec_from_file_location("tre", TEST_MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "_build_vectors"):
        raise SystemExit("test_reducer_equivalence.py does not expose _build_vectors")
    return mod._build_vectors
def sha256(s): return hashlib.sha256(s.encode()).hexdigest()
def main():
    regenerated = json.dumps(load_builder()(), indent=2, sort_keys=True) + "\n"
    committed = open(FIXTURE, encoding="utf-8").read()
    r, c = sha256(regenerated), sha256(committed)
    print(f"regenerated fixture sha256: {r}")
    print(f"committed  fixture sha256: {c}")
    if r != c:
        print("SEMANTIC CERTIFICATE STALE", file=sys.stderr)
        return 1
    print("reducer_vectors semantic certificate: fresh")
    return 0
if __name__ == "__main__": sys.exit(main())
