"""No-direct-repair gate gates — the static scan must be NON-VACUOUS:
it must really scan certification/, evolution/, compiler/ and catch
remediation-style writes while permitting evidence + mkdtemp writes."""
import textwrap
import sys

import pytest

sys.path.insert(0, "release/gates/cbc1")
import check_no_direct_repair as gate


def _probe(source: str):
    import tempfile, os
    d = tempfile.mkdtemp(prefix="ndr-probe-")
    p = os.path.join(d, "mod.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(source))
    return gate._scan_file(p)


def test_scan_dirs_exist():
    import os

    root = gate._repo_root()
    for d in gate.SCAN_DIRS:
        assert os.path.isdir(os.path.join(root, d)), f"{d} missing at {root}"


def test_repo_root_resolution():
    assert gate._repo_root().endswith("New folder (2)") or gate._repo_root() != ""
    assert gate._repo_root() != "release"


def test_tree_is_clean():
    assert gate.run_scan() == []


def test_catches_remediation_write():
    v = _probe(
        """
        def repair(trial_id):
            with open("app/main.py", "w", encoding="utf-8") as f:
                f.write("print('patched')")
        """
    )
    assert v


def test_catches_pathlib_literal_remediation():
    v = _probe(
        """
        from pathlib import Path
        p = "generated_src/routes.py"
        with open(p, "w", encoding="utf-8") as f:
            f.write("x = 1")
        """
    )
    assert v


def test_allows_evidence_write():
    v = _probe(
        """
        DEFAULT_AGG = "release/evidence/cbc1-x-aggregate.json"
        def record(out_path=DEFAULT_AGG):
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("{}")
        """
    )
    assert v == []


def test_allows_mkdtemp_materialization():
    v = _probe(
        """
        import os, tempfile
        def build(repo):
            d = tempfile.mkdtemp(prefix="cbc1-x-")
            for p, c in repo.files.items():
                full = os.path.join(d, p)
                with open(full, "w", encoding="utf-8") as fh:
                    fh.write(c)
        """
    )
    assert v == []


def test_allows_safe_candidate_path_materialization():
    # _safe_candidate_path(d, p) over a mkdtemp workspace is provenance-safe
    # forward artifact creation, exactly like os.path.join on that workspace.
    v = _probe(
        """
        import os, tempfile
        from certification.campaign.runner import _safe_candidate_path
        def build(repo):
            d = tempfile.mkdtemp(prefix="cbc1-x-")
            for p, c in repo.files.items():
                full = _safe_candidate_path(d, p)
                os.makedirs(os.path.dirname(full), exist_ok=True)
                with open(full, "w", encoding="utf-8") as fh:
                    fh.write(c)
        """
    )
    assert v == []


def test_catches_safe_candidate_path_over_untrusted_root():
    # The sanitizer itself must not launder writes rooted outside a
    # benign temp/evidence expression.
    v = _probe(
        """
        from certification.campaign.runner import _safe_candidate_path
        def rematerialize(trial_dir):
            full = _safe_candidate_path(trial_dir, "candidate/app.py")
            with open(full, "w", encoding="utf-8") as fh:
                fh.write("patched")
        """
    )
    assert v