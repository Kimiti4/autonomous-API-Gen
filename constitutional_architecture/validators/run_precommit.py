"""
Pre-commit runner for constitutional validation.

Called by the git pre-commit hook. Scans staged files for violations
of the 7 constitutional axioms.
"""

import os
import subprocess
import sys

from constitutional_architecture.validators.constitution_validator import ConstitutionValidator


def get_staged_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, cwd=os.getcwd(),
    )
    if result.returncode != 0:
        return []
    return [f.strip() for f in result.stdout.splitlines() if f.strip()]


def main() -> int:
    repo_root = os.getcwd()
    validator = ConstitutionValidator(repo_root)
    staged = get_staged_files()

    if not staged:
        print("No staged files to validate.")
        return 0

    python_files: dict[str, str] = {}
    for filepath in staged:
        full_path = os.path.join(repo_root, filepath)
        if filepath.endswith(".py") and os.path.exists(full_path):
            with open(full_path, encoding="utf-8") as f:
                python_files[filepath] = f.read()

    result = validator.validate_all(python_files=python_files)

    for v in result.violations:
        label = "ERROR" if v.severity == "error" else "WARN"
        location = f" [{v.file}:{v.line}]" if v.file else ""
        print(f"  [{label}] Axiom {v.axiom}: {v.description}{location}")

    if not result.passed:
        print(f"\nFAILED: {len([v for v in result.violations if v.severity == 'error'])} constitutional error(s)")
        return 1

    if result.violations:
        print(f"\nPASSED: {len(result.violations)} warning(s) — review recommended")
    else:
        print("PASSED: No constitutional violations found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
