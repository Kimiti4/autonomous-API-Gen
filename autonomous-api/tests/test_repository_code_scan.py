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


def test_scan_flags_unassociated_jsx_label_with_line_evidence():
    source = """<div>
  <label>Full Name</label>
  <input type="text" name="name" />
</div>"""
    scan = scan_repository([("RegisterPage.jsx", source)])
    finding = next(f for f in scan.findings if f.rule == "unassociated-jsx-label")
    assert finding.line == 2
    assert finding.category == "accessibility-risk"
    assert "label" in finding.evidence[1]


def test_scan_does_not_flag_associated_jsx_label():
    source = """<label htmlFor="register-name">Full Name</label>
<input id="register-name" type="text" />"""
    scan = scan_repository([("RegisterPage.jsx", source)])
    assert not any(f.rule == "unassociated-jsx-label" for f in scan.findings)


def test_scan_flags_e2e_skip_and_permissive_registration_outcome():
    source = """if (await nameInput.isVisible()) await nameInput.fill('newuser');
const landedOnFeed = url.endsWith('/') || url.includes('/login') || url.includes('/register');
expect(landedOnFeed).toBeTruthy();"""
    scan = scan_repository([("registration.spec.js", source)])
    rules = {f.rule for f in scan.findings}
    assert "conditional-e2e-interaction" in rules
    assert "permissive-registration-outcome" in rules


def test_scan_no_longer_flags_repaired_registration_journey():
    source = """await page.getByLabel(/full name/i).fill('newuser');
await expect(page).toHaveURL(/\\/login$/);
expect(registrationPayload).toMatchObject({ username: 'newuser' });"""
    scan = scan_repository([("registration.spec.js", source)])
    assert not any(f.rule in {
        "conditional-e2e-interaction", "permissive-registration-outcome"
    } for f in scan.findings)
