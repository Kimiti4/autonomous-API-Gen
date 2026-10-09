from app.engine.repository_code_scan import scan_repository


def test_unassociated_label_is_reported_with_location():
    source = """<div>
  <label>Full Name</label>
  <input type="text" name="name" />
</div>"""
    scan = scan_repository([("RegisterPage.jsx", source)])
    finding = next(f for f in scan.findings if f.rule == "unassociated-jsx-label")
    assert finding.line == 2
    assert finding.category == "accessibility-risk"
    assert "label" in finding.evidence[1]


def test_associated_label_is_not_reported():
    source = """<label htmlFor="register-name">Full Name</label>
<input id="register-name" type="text" />"""
    scan = scan_repository([("RegisterPage.jsx", source)])
    assert not any(f.rule == "unassociated-jsx-label" for f in scan.findings)


def test_conditional_e2e_action_and_weak_outcome_are_reported():
    source = """if (await nameInput.isVisible()) await nameInput.fill('newuser');
const landedOnFeed = url.endsWith('/') || url.includes('/login') || url.includes('/register');
expect(landedOnFeed).toBeTruthy();"""
    scan = scan_repository([("registration.spec.js", source)])
    rules = {f.rule for f in scan.findings}
    assert "conditional-e2e-interaction" in rules
    assert "permissive-registration-outcome" in rules


def test_strict_registration_outcome_has_no_integrity_finding():
    source = """await page.getByLabel(/full name/i).fill('newuser');
await expect(page).toHaveURL(/\\/login$/);
expect(registrationPayload).toMatchObject({ username: 'newuser' });"""
    scan = scan_repository([("registration.spec.js", source)])
    assert not any(f.rule in {
        "conditional-e2e-interaction", "permissive-registration-outcome"
    } for f in scan.findings)
