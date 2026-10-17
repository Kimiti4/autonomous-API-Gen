"""Contract tests for the general-purpose generated-code quality inspector."""
from compiler.core.code_quality import CodeQualityInspector, QualitySeverity
from compiler.core.repository import GeneratedRepository, build_repository


def _inspect(files):
    return CodeQualityInspector().inspect(build_repository(files))


def test_valid_python_repository_passes_and_is_bound_to_exact_content():
    repo = build_repository({"app/main.py": "def add(a: int, b: int) -> int:\n    return a + b\n"})
    report = CodeQualityInspector().inspect(repo)

    assert report.passed
    assert report.repository_hash == repo.content_hash
    assert report.declared_repository_hash == repo.content_hash
    assert report.analyzed_languages == ["python"]
    assert report.findings == []


def test_python_syntax_error_blocks_quality_report():
    report = _inspect({"app/main.py": "def broken(:\n    pass\n"})

    assert not report.passed
    assert any(f.rule_id == "QRY-SYNTAX-PY-001" and f.severity == QualitySeverity.ERROR for f in report.findings)


def test_path_traversal_and_case_collisions_block_report():
    report = _inspect({
        "../escape.py": "print('unsafe path')\n",
        "App/Main.py": "print('one')\n",
        "app/main.py": "print('two')\n",
    })

    assert not report.passed
    assert any(f.rule_id == "QRY-ART-001" for f in report.findings)
    assert any(f.rule_id == "QRY-ART-002" for f in report.findings)


def test_secret_material_and_placeholder_tests_are_detected():
    report = _inspect({
        "app/service.py": "TOKEN = 'ghp_" + "A" * 36 + "'\nraise NotImplementedError()\n",
        "app/tests/test_service.py": "def test_service():\n    assert True\n",
    })

    assert not report.passed
    assert any(f.rule_id == "QRY-SEC-003" and f.severity == QualitySeverity.BLOCKER for f in report.findings)
    assert any(f.rule_id == "QRY-QUAL-001" and f.severity == QualitySeverity.ERROR for f in report.findings)
    assert any(f.rule_id == "QRY-TEST-001" and f.severity == QualitySeverity.ERROR for f in report.findings)


def test_missing_or_mismatched_content_hash_blocks_report():
    missing = GeneratedRepository(files={"app/main.py": "print('hi')\n"})
    mismatched = GeneratedRepository(files={"app/main.py": "print('hi')\n"}, content_hash="0" * 64)

    assert not CodeQualityInspector().inspect(missing).passed
    assert any(f.rule_id == "QRY-INT-002" for f in CodeQualityInspector().inspect(missing).findings)
    assert not CodeQualityInspector().inspect(mismatched).passed
    assert any(f.rule_id == "QRY-INT-001" for f in CodeQualityInspector().inspect(mismatched).findings)


def test_unsupported_language_analysis_is_explicit_when_required():
    repo = build_repository({"frontend/App.tsx": "export default function App() { return <main /> }\n"})
    report = CodeQualityInspector().inspect(repo)
    strict = CodeQualityInspector().inspect(repo, require_complete_language_analysis=True)

    assert report.passed
    assert report.unparsed_languages == ["typescript"]
    assert not strict.passed
    assert any(f.rule_id == "QRY-COVERAGE-001" for f in strict.findings)


def test_python_quality_checks_find_mutable_defaults_and_swallowed_exceptions():
    report = _inspect({
        "app/service.py": (
            "def collect(items=[]):\n"
            "    try:\n"
            "        risky()\n"
            "    except:\n"
            "        pass\n"
            "    return items\n"
        )
    })

    assert not report.passed
    assert {f.rule_id for f in report.findings} >= {
        "QRY-PY-QUAL-001", "QRY-PY-QUAL-002", "QRY-PY-QUAL-003"
    }
