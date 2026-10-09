"""Fail-closed, rule-guided minimal repair trial for the pinned JamiiLink baseline.

This tool edits only a caller-supplied disposable workspace. It never checks out,
pushes, or writes to the upstream JamiiLink repository. Every transformation has
an exact precondition and aborts if the expected baseline shape has drifted.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re
import sys

PAGE = Path("iyf-s10-week-09-Kimiti4/src/pages/RegisterPage.jsx")
JOURNEY = Path(
    "iyf-s10-week-09-Kimiti4/e2e/journeys/"
    "jn-01.register-feed-discover-profile-alerts.spec.js"
)

OLD_INTERACTION = """    const nameInput = page.getByLabel(/username|name/i);
    const emailInput = page.getByLabel(/email/i);
    const passwordInput = page.getByRole('textbox', { name: 'Password', exact: true });

    if (await nameInput.isVisible()) await nameInput.fill('newuser');
    if (await emailInput.isVisible()) await emailInput.fill('new@jamii.link');
    if (await passwordInput.isVisible()) await passwordInput.fill('TestPass123!');

    const submitBtn = page.getByRole('button', { name: /register|sign up|create/i });
    if (await submitBtn.isVisible()) await submitBtn.click();

    // Level C: Outcome - navigation to feed
    await page.waitForTimeout(1500);
    const url = page.url();
    const landedOnFeed = url.endsWith('/') || url.includes('/login') || url.includes('/register');
    expect(landedOnFeed).toBeTruthy();"""

NEW_INTERACTION = """    await page.getByLabel(/full name/i).fill('newuser');
    await page.getByLabel(/email/i).fill('new@jamii.link');
    await page.getByLabel(/^password/i).fill('TestPass123!');
    await page.getByLabel(/confirm password/i).fill('TestPass123!');
    await page.getByRole('button', { name: /join jamiilink/i }).click();

    // Level C: Outcome - successful registration should reach the login page.
    await expect(page).toHaveURL(/\\/login$/);
    expect(registrationPayload).toMatchObject({ username: 'newuser', email: 'new@jamii.link' });
    expect(registrationPayload.password).toBe('TestPass123!');"""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def require_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one anchor, found {count}; no repair applied")
    return text.replace(old, new, 1)


def repair_labels(source: str) -> tuple[str, int]:
    pattern = re.compile(
        r"<label>([^<]+)</label>(\\s*)(<input\\b[^>]*\\bname=\"([^\"]+)\"[^>]*>)"
    )
    names = {"name", "email", "location", "password", "confirmPassword"}
    seen: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        label, whitespace, input_tag, field_name = match.groups()
        if field_name not in names or field_name in seen:
            raise ValueError(f"unexpected or duplicate registration field: {field_name}")
        seen.add(field_name)
        field_id = "register-" + ("confirm-password" if field_name == "confirmPassword" else field_name)
        label = f'<label htmlFor="{field_id}">{label}</label>'
        input_tag = re.sub(r"\\s+id=\"[^\"]*\"", "", input_tag)
        input_tag = input_tag.replace("<input", f'<input id="{field_id}"', 1)
        return label + whitespace + input_tag

    repaired, count = pattern.subn(replace, source)
    if count != 5 or seen != names:
        raise ValueError(
            f"label repair precondition failed: expected 5 unique fields, found {count} ({sorted(seen)}); "
            "no files should be accepted as repaired"
        )
    return repaired, count


def generate(workspace: Path, patch_path: Path) -> dict:
    page_path = workspace / PAGE
    journey_path = workspace / JOURNEY
    if not page_path.is_file() or not journey_path.is_file():
        raise FileNotFoundError("workspace does not contain both pinned registration target files")

    before = {PAGE: page_path.read_text(encoding="utf-8"), JOURNEY: journey_path.read_text(encoding="utf-8")}
    page_after, label_count = repair_labels(before[PAGE])

    journey_after = before[JOURNEY]
    journey_after = require_once(
        journey_after,
        """    await page.route('**/api/auth/register', (route) =>
      route.fulfill({""",
        """    let registrationPayload = null;
    await page.route('**/api/auth/register', (route) => {
      registrationPayload = route.request().postDataJSON();
      return route.fulfill({""",
        "capture registration request payload",
    )
    journey_after = require_once(
        journey_after,
        """      })
    );

    // Level A: Reachability - register page loads
    await page.goto('/register');
    await expect(page.getByRole('heading', { name: /join jamii/i })).toBeVisible();""",
        """      });
    });

    // Level A: Reachability - register page loads
    await page.goto('/register');
    await expect(page.getByRole('heading', { name: /join.*jamii/i })).toBeVisible();""",
        "capture route closure and stabilize heading locator",
    )
    journey_after = require_once(journey_after, OLD_INTERACTION, NEW_INTERACTION, "strict registration journey")
    changes = {PAGE: page_after, JOURNEY: journey_after}
    if any(before[path] == changes[path] for path in changes):
        raise ValueError("repair did not change every intended file")

    patch_lines: list[str] = []
    for path in (PAGE, JOURNEY):
        patch_lines.extend(difflib.unified_diff(
            before[path].splitlines(keepends=True),
            changes[path].splitlines(keepends=True),
            fromfile=f"a/{path.as_posix()}",
            tofile=f"b/{path.as_posix()}",
        ))
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    patch_path.write_text("".join(patch_lines), encoding="utf-8")

    # Re-read and validate after all preconditions pass; no partial write on anchor failure.
    page_path.write_text(changes[PAGE], encoding="utf-8")
    journey_path.write_text(changes[JOURNEY], encoding="utf-8")
    report = {
        "schema": "esap.existing-codebase-repair-trial.v1",
        "mode": "disposable-workspace-only",
        "upstream_repository_modified": False,
        "patch_applied_to_disposable_workspace": True,
        "human_review_required_before_external_write": True,
        "repair_engine": "deterministic-rule-guided-transformations",
        "independent_general_reasoning_claimed": False,
        "changes": [
            {"path": path.as_posix(), "before_sha256": sha(before[path]), "after_sha256": sha(changes[path])}
            for path in (PAGE, JOURNEY)
        ],
        "label_associations_repaired": label_count,
        "patch_path": str(patch_path),
        "verification_required": ["static rescan", "npm run lint", "npm run build", "Playwright E2E"],
    }
    (patch_path.parent / "repair-trial-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--patch-out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = generate(args.workspace.resolve(), args.patch_out.resolve())
    except (OSError, ValueError) as exc:
        print(json.dumps({"verdict": "BLOCKED", "reason": str(exc), "patch_applied": False}, indent=2))
        return 2
    print(json.dumps({"verdict": "PATCH_GENERATED", **report}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
