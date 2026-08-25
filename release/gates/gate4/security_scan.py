#!/usr/bin/env python3
"""Gate 4 — security boundary static scan.

Fails on: token-in-URL, internal cluster DNS, stub auth in production paths,
permissive CSP, and cluster DNS in shipped artifacts.

Two modes:
  default       source + CSP + dist scan. Pre-build, dist is usually absent;
                the dist scan then emits a loud WARNING and is deferred to the
                post-build --dist-only run (Gate 6). Source/CSP still enforced.
  --dist-only   scans ONLY shipped dist artifacts. Fails if no dist is present,
                because a post-build shipped-artifact scan with nothing to scan
                would be a vacuous pass.

Exit codes: 0 clean | 1 violations (or vacuous --dist-only) | 2 usage error.

Measures reality; never fabricates. A certification gate must not pass by
skipping itself silently.
"""
import argparse
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SOURCE_DIRS = ["dashboard/src", "observation-client/src", "autonomous-api/app"]
DIST_DIRS = ["dashboard/dist", "observation-client/dist"]
NGINX_CONF = "dashboard/nginx.conf"

FORBIDDEN_SOURCE = [
    (r"[?&]access_token=", "access_token in URL query"),
    (r"[?&]token=", "token in URL query"),
    (r"\.svc\.cluster\.local", "internal cluster DNS hostname"),
    (r"\bStubAuthProvider\s*\(", "stub auth provider instantiated"),
]
EXCLUDE = [r"/tests?/", r"\.test\.", r"conftest"]


def iter_files(dirs, exts):
    for d in dirs:
        full = os.path.join(REPO, d)
        if not os.path.isdir(full):
            continue
        for root, _, files in os.walk(full):
            for f in files:
                if any(f.endswith(e) for e in exts):
                    yield os.path.join(root, f)


def excluded(path):
    return any(re.search(p, path) for p in EXCLUDE)


def scan_source():
    out = []
    for path in iter_files(SOURCE_DIRS, {".ts", ".tsx", ".py"}):
        if excluded(path):
            continue
        text = open(path, encoding="utf-8", errors="ignore").read()
        for pat, desc in FORBIDDEN_SOURCE:
            for m in re.finditer(pat, text):
                out.append(f"{os.path.relpath(path, REPO)}: {desc} ({m.group(0)!r})")
    return out


def scan_dist_cluster_dns():
    """Scan shipped dist artifacts for internal cluster DNS leakage.

    Returns (findings, dist_dirs_scanned). dist_dirs_scanned == 0 means no dist
    artifacts existed, so nothing was actually scanned.
    """
    out = []
    pat = re.compile(r"\.svc\.cluster\.local")
    scanned = 0
    for d in DIST_DIRS:
        full = os.path.join(REPO, d)
        if not os.path.isdir(full):
            continue
        scanned += 1
        for root, _, files in os.walk(full):
            for f in files:
                p = os.path.join(root, f)
                try:
                    text = open(p, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                if pat.search(text):
                    out.append(f"{os.path.relpath(p, REPO)}: cluster DNS in shipped artifact")
    return out, scanned


def check_csp():
    conf = os.path.join(REPO, NGINX_CONF)
    if not os.path.isfile(conf):
        return [f"{NGINX_CONF}: not found"]
    text = open(conf).read()
    m = re.search(r'Content-Security-Policy\s+"([^"]+)"', text)
    if not m:
        return [f"{NGINX_CONF}: no Content-Security-Policy header"]
    csp, out = m.group(1), []
    for directive in csp.split(";"):
        directive = directive.strip()
        if not directive:
            continue
        name, _, value = directive.partition(" ")
        if name in {"default-src", "connect-src", "script-src"} and "*" in value.split():
            out.append(f"CSP overly permissive: {directive}")
    if "connect-src" not in csp:
        out.append("CSP missing explicit connect-src")
    return out


def run_all():
    source_findings = scan_source()
    dist_findings, dist_scanned = scan_dist_cluster_dns()
    csp_findings = check_csp()

    if dist_scanned == 0:
        print(
            "WARNING: no dist artifacts present — cluster-DNS dist scan SKIPPED.\n"
            "         Gate 4 runs pre-build; the authoritative shipped-artifact scan\n"
            "         runs post-build in Gate 6 via `--dist-only`.",
            file=sys.stderr,
        )

    findings = source_findings + dist_findings + csp_findings
    if findings:
        print("GATE 4 SECURITY VIOLATIONS:", file=sys.stderr)
        for f in findings:
            print("  " + f, file=sys.stderr)
        return 1

    print(
        f"Gate 4 static security scan: clean "
        f"(source_findings=0 csp_findings=0 dist_scanned={dist_scanned} dist_findings=0)"
    )
    return 0


def run_dist_only():
    dist_findings, dist_scanned = scan_dist_cluster_dns()

    if dist_scanned == 0:
        print(
            "GATE 4 (--dist-only) FAILURE: no dist artifacts found to scan.\n"
            "The post-build shipped-artifact scan requires dashboard/ and\n"
            "observation-client/ builds to have produced dist/. Refusing to pass\n"
            "a vacuous scan.",
            file=sys.stderr,
        )
        return 1

    if dist_findings:
        print("GATE 4 (--dist-only) SHIPPED-ARTIFACT VIOLATIONS:", file=sys.stderr)
        for f in dist_findings:
            print("  " + f, file=sys.stderr)
        return 1

    print(f"Gate 4 (--dist-only) shipped-artifact scan: clean ({dist_scanned} dist dir(s) scanned)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Gate 4 security boundary scan")
    ap.add_argument(
        "--dist-only",
        action="store_true",
        help="scan only shipped dist artifacts (post-build); fails if no dist present",
    )
    args = ap.parse_args()
    if args.dist_only:
        return run_dist_only()
    return run_all()


if __name__ == "__main__":
    sys.exit(main())
