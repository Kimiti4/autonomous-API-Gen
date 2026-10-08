import ast
from pathlib import Path

COMPILER_DIR = Path("tiannara/application/compiler")


def test_compiler_modules_parse_without_syntax_errors():
    failures = []
    for path in sorted(COMPILER_DIR.glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.append(f"{path}: {exc}")
    assert not failures, "\n".join(failures)


def test_compiler_sources_do_not_contain_known_invalid_php_namespace_escape():
    offenders = []
    for path in sorted(COMPILER_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "\\Illuminate\\Database" in text and "\\\\Illuminate\\Database" not in text:
            offenders.append(str(path))
    assert not offenders, f"Unescaped PHP namespace literals: {offenders}"
