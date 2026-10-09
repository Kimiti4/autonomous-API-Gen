"""SqlMigrationsBackend -- schema migration tooling derived from the ISR.

Consumes the typed SystemModel's data models and deterministically emits:

  * ``<slug>/migrations/0001_init.sql``  -- DDL for every data model (abstract
    field types lowered to portable SQL types, identifiers become primary
    keys, enumerations become CHECK constraints, optionality becomes
    NULLability);
  * ``<slug>/migrations/apply.py``       -- idempotent applier tracking
    applied files in a ``schema_migrations`` ledger table;
  * ``<slug>/migrations/tests/...``      -- executable pytest suite that
    cross-checks the generated DDL against the generated expectations, applies
    it to a scratch database, compares SQLite's own schema (PRAGMA) with the
    declared shape, proves idempotence, and exercises the CHECK constraints.

Design constraints (mirrors the FastAPI/Go backends):
  * structure derives solely from the ISR; nothing is hard-coded per product;
  * the bundle roots at ``<slug>/migrations/`` so multi-backend fleets sharing
    one project root never collide;
  * generated tests pass on first run against the generated code itself.
"""

from __future__ import annotations

from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.capability_manifest import BundleCapability, CapabilityManifest
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    DataModelSpec,
    FieldSpec,
    SystemModel,
)

from .naming import pluralize, slugify, snake_case

_SQL_TYPE: dict[AbstractFieldType, str] = {
    AbstractFieldType.IDENTIFIER: "TEXT",
    AbstractFieldType.TEXT: "TEXT",
    AbstractFieldType.INTEGER: "INTEGER",
    AbstractFieldType.DECIMAL: "NUMERIC",
    AbstractFieldType.BOOLEAN: "INTEGER",
    AbstractFieldType.TIMESTAMP: "TEXT",
    AbstractFieldType.ENUMERATION: "TEXT",
    AbstractFieldType.REFERENCE: "TEXT",
    AbstractFieldType.BINARY: "BLOB",
    AbstractFieldType.DOCUMENT: "TEXT",
}


def _table_name(model: DataModelSpec) -> str:
    return pluralize(snake_case(model.name))


def _pk_name(model: DataModelSpec) -> str | None:
    fields = _effective_fields(model)
    for field in fields:
        if field.name == "id":
            return field.name
    for field in fields:
        if field.type is AbstractFieldType.IDENTIFIER:
            return field.name
    return None


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _effective_fields(model: DataModelSpec) -> list[FieldSpec]:
    if model.fields:
        return list(model.fields)
    return [FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER)]


def _sample_value(field: FieldSpec) -> str | int | float | bytes:
    kind = field.type
    if kind is AbstractFieldType.ENUMERATION and field.enumeration_values:
        return field.enumeration_values[0]
    if kind is AbstractFieldType.INTEGER:
        return 1
    if kind is AbstractFieldType.BOOLEAN:
        return 1
    if kind is AbstractFieldType.DECIMAL:
        return 12.5
    if kind is AbstractFieldType.TIMESTAMP:
        return "2026-01-01T00:00:00"
    if kind is AbstractFieldType.DOCUMENT:
        return '{"seed": true}'
    if kind is AbstractFieldType.BINARY:
        return b"seed"
    return "seed"


class SqlMigrationsBackend:
    """Deterministic, model-free compiler backend for schema migrations."""

    backend_id = "sql_migrations"

    # -- public: pure product ---------------------------------------------

    def generate(self, system_model: SystemModel) -> CompilationResult:
        slug = slugify(system_model.system_name)
        models = system_model.data_models
        root = f"{slug}/migrations"
        files: dict[str, str] = {
            f"{root}/__init__.py": "",
            f"{root}/0001_init.sql": self._ddl(models),
            f"{root}/apply.py": self._apply_py(),
            f"{root}/tests/__init__.py": "",
            f"{root}/tests/test_migrations.py": self._tests_py(slug, models),
        }
        return CompilationResult(
            backend_id=self.backend_id,
            system_name=slug,
            files=files,
            capability_manifest=self._manifest(),
        )

    def build_profile(self, system_name: str) -> BackendBuildProfile:
        slug = slugify(system_name)
        return BackendBuildProfile(
            language="python",
            required_files=(
                f"{slug}/migrations/0001_init.sql",
                f"{slug}/migrations/apply.py",
            ),
            verifier_kind="python",
            build_command=["python", "-m", "pip", "install", "-q", "pytest"],
            test_command=["python", "-m", "pytest", "-q", f"{slug}/migrations/tests"],
            runtime_image=None,
            requires_build_phase=True,
        )

    def declaration(self) -> BackendCapabilityDeclaration:
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.DATABASE_MIGRATION],
            capabilities=[
                BundleCapability.DATABASE_MIGRATION,
                BundleCapability.BUILD,
                BundleCapability.TEST,
                BundleCapability.DOCUMENTATION,
            ],
            quality_profile=0.8,
            metadata={"language": "python", "style": "sql-migrations"},
        )

    @property
    def name(self) -> str:
        return self.backend_id

    # -- DDL ---------------------------------------------------------------

    def _ddl(self, models: list[DataModelSpec]) -> str:
        lines = [
            "-- Schema migrations derived from the typed ISR.",
            "-- Deterministic: identical input models yield identical output.",
            "",
        ]
        for model in models:
            table = _table_name(model)
            pk = _pk_name(model)
            lines.append(f'CREATE TABLE IF NOT EXISTS "{table}" (')
            columns: list[str] = []
            for field in _effective_fields(model):
                column = f'    "{field.name}" {_SQL_TYPE.get(field.type, "TEXT")}'
                if pk is not None and field.name == pk:
                    column += " PRIMARY KEY"
                else:
                    if field.required:
                        column += " NOT NULL"
                    if (
                        field.type is AbstractFieldType.ENUMERATION
                        and field.enumeration_values
                    ):
                        values = ", ".join(
                            _sql_literal(v) for v in field.enumeration_values
                        )
                        column += f' CHECK ("{field.name}" IN ({values}))'
                columns.append(column)
            lines.append(",\n".join(columns))
            lines.append(");")
            lines.append("")
        return "\n".join(lines)

    # -- file generators ---------------------------------------------------

    def _apply_py(self) -> str:
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import sqlite3",
                "import sys",
                "from pathlib import Path",
                "",
                "MIGRATIONS_DIR = Path(__file__).resolve().parent",
                "",
                "",
                "def migration_files() -> list[Path]:",
                '    return sorted(MIGRATIONS_DIR.glob("*.sql"))',
                "",
                "",
                "def apply(db_path: str) -> list[str]:",
                '    connection = sqlite3.connect(db_path)',
                "    try:",
                '        connection.execute(',
                '            "CREATE TABLE IF NOT EXISTS schema_migrations ("',
                '            "name TEXT PRIMARY KEY, "',
                '            "applied_at TEXT DEFAULT (datetime(\'now\')))"',
                "        )",
                '        applied = {',
                '            row[0]',
                '            for row in connection.execute(',
                '                "SELECT name FROM schema_migrations"',
                '            )',
                "        }",
                "        executed: list[str] = []",
                "        for path in migration_files():",
                "            if path.name in applied:",
                "                continue",
                "            connection.executescript(path.read_text(encoding='utf-8'))",
                '            connection.execute(',
                '                "INSERT INTO schema_migrations (name) VALUES (?)",',
                "                (path.name,),",
                "            )",
                "            connection.commit()",
                "            executed.append(path.name)",
                "        return executed",
                "    finally:",
                "        connection.close()",
                "",
                "",
                'if __name__ == "__main__":',
                '    database = sys.argv[1] if len(sys.argv) > 1 else "app.db"',
                "    print(apply(database))",
                "",
            ]
        )

    def _tests_py(self, slug: str, models: list[DataModelSpec]) -> str:
        expected: dict[str, list[str]] = {}
        for model in models:
            expected[_table_name(model)] = [f.name for f in _effective_fields(model)]
        enum_case = self._enum_case(models)
        imports = ["import re", "import sqlite3"]
        if enum_case:
            imports.append("import pytest")
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                *imports,
                "",
                f"from {slug}.migrations.apply import apply, migration_files",
                "",
                f"EXPECTED = {expected!r}",
                "",
                "",
                "def _ddl_text() -> str:",
                '    return "\\n".join(',
                '        path.read_text(encoding="utf-8")',
                "        for path in migration_files()",
                "    )",
                "",
                "",
                "def test_migration_file_is_present():",
                '    assert [path.name for path in migration_files()] == ["0001_init.sql"]',
                "",
                "",
                "def test_ddl_defines_exactly_the_expected_tables():",
                '    created = re.findall(\'CREATE TABLE IF NOT EXISTS "([^"]+)"\', _ddl_text())',
                "    assert set(created) == set(EXPECTED)",
                "",
                "",
                "def test_ddl_columns_match_expected_shape():",
                "    text = _ddl_text()",
                "    for table, columns in EXPECTED.items():",
                "        match = re.search(",
                '            rf\'CREATE TABLE IF NOT EXISTS "{table}" \\((.*?)\\n\\);\',',
                "            text,",
                "            re.S,",
                "        )",
                "        assert match is not None, table",
                '        parsed = re.findall(r\'^    "([^"]+)" \', match.group(1), re.M)',
                "        assert parsed == columns",
                "",
                "",
                "def test_apply_creates_the_declared_schema(tmp_path):",
                '    db = str(tmp_path / "app.db")',
                '    assert apply(db) == ["0001_init.sql"]',
                '    connection = sqlite3.connect(db)',
                "    try:",
                "        for table, columns in EXPECTED.items():",
                "            actual = [",
                "                row[1]",
                '                for row in connection.execute(f\'PRAGMA table_info("{table}")\')',
                "            ]",
                "            assert actual == columns",
                "    finally:",
                "        connection.close()",
                "",
                "",
                "def test_apply_is_idempotent(tmp_path):",
                '    db = str(tmp_path / "app.db")',
                "    apply(db)",
                "    assert apply(db) == []",
                "",
            ]
            + enum_case
        )

    def _enum_case(self, models: list[DataModelSpec]) -> list[str]:
        for model in models:
            pk = _pk_name(model)
            enum_field = next(
                (
                    f
                    for f in model.fields
                    if f.type is AbstractFieldType.ENUMERATION and f.enumeration_values
                ),
                None,
            )
            if enum_field is None or pk is None:
                continue
            table = _table_name(model)
            required = [
                f
                for f in _effective_fields(model)
                if f.required and f.name != pk and f.name != enum_field.name
            ]
            columns = [pk, enum_field.name] + [f.name for f in required]
            invalid = enum_field.enumeration_values[0] + "_invalid"
            placeholders = ", ".join("?" for _ in columns)
            column_sql = ", ".join(f'"{name}"' for name in columns)
            valid_values: list[str | int | float | bytes] = [
                "seed-row",
                enum_field.enumeration_values[0],
            ]
            valid_values.extend(_sample_value(f) for f in required)
            invalid_values = list(valid_values)
            invalid_values[1] = invalid
            valid_sql = repr(valid_values)
            invalid_sql = repr(invalid_values)
            return [
                "",
                "def test_check_constraint_rejects_unknown_enumeration_values(tmp_path):",
                '    db = str(tmp_path / "app.db")',
                "    apply(db)",
                '    connection = sqlite3.connect(db)',
                "    try:",
                f"        connection.execute(",
                f'            \'INSERT INTO "{table}" ({column_sql}) VALUES ({placeholders})\',',  # nosec B608
                f"            {valid_sql},",
                "        )",
                "        connection.commit()",
                "        with pytest.raises(sqlite3.IntegrityError):",
                f"            connection.execute(",
                f'                \'INSERT INTO "{table}" ({column_sql}) VALUES ({placeholders})\',',  # nosec B608
                f"                {invalid_sql},",
                "            )",
                "    finally:",
                "        connection.close()",
                "",
            ]
        return []

    def _manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[
                BundleCapability.DATABASE_MIGRATION,
                BundleCapability.BUILD,
                BundleCapability.TEST,
            ],
            metadata={"language": "python", "style": "sql-migrations"},
        )
