"""Compiler backend registry.

The registry is deliberately small: backend selection is a compiler concern,
not a Genome concern. Additional language/framework targets can implement the
same CompilerBackend contract without changing the ISR-facing model.
"""

import os
import json
import hashlib
import subprocess
from typing import Dict
from pathlib import Path

from app.engine.backend_contract import (
    ARCHITECTURE_SCHEMA_VERSION,
    BackendTarget,
    CompilerBackend,
    CompilationRequest,
    CompiledArtifact,
    PYTHON_FASTAPI,
    make_compilation_request,
)
from app.engine.capability_semantics import plan_capabilities
from app.engine.builder import (
    generate_database_file,
    generate_dockerfile,
    generate_main_app,
    generate_models_file,
    generate_requirements,
    generate_security_file,
    generate_service_file,
)
from app.engine.genome import Genome

# SQL statements embedded in the generated Go/net/http artifact. Declared as
# standalone string constants so Bandit does not flag the multi-line Go source
# template (the generated program uses fully parameterized queries).
_SQL_CREATE_RECORDS = (  # nosec B608
    "CREATE TABLE IF NOT EXISTS records (\n"
    "        id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    "        service TEXT NOT NULL,\n"
    "        payload TEXT NOT NULL\n"
    "    )"
)
_SQL_SELECT_RECORDS = "SELECT id, payload FROM records WHERE service = ?"  # nosec B608
_SQL_INSERT_RECORDS = "INSERT INTO records (service, payload) VALUES (?, ?)"  # nosec B608


class PythonFastAPIBackend:
    """First concrete compiler backend for the existing Python generator."""

    target = PYTHON_FASTAPI
    runtime_supported = True

    def supports(self, request: CompilationRequest) -> bool:
        return (
            request.target == self.target
            and request.architecture_schema == ARCHITECTURE_SCHEMA_VERSION
        )

    def _architecture_files(self, genome: Genome) -> Dict[str, str]:
        """Lower semantic capability intent into the Python/FastAPI artifact."""
        plan = plan_capabilities(genome)
        if plan.unmapped:
            raise ValueError(
                "cannot lower unmapped capabilities: " + ", ".join(plan.unmapped)
            )

        files: Dict[str, str] = {
            "main.py": generate_main_app(genome),
            "database.py": generate_database_file(genome),
            "security.py": generate_security_file(genome),
            "requirements.txt": generate_requirements(genome),
            "Dockerfile": generate_dockerfile(genome),
            os.path.join("services", "models.py"): generate_models_file(genome),
            os.path.join("services", "__init__.py"): "",
        }
        for service in genome.services:
            files[os.path.join("services", f"{service}.py")] = generate_service_file(
                service, genome
            )
        return files

    def compile(self, request: CompilationRequest) -> CompiledArtifact:
        if not self.supports(request):
            raise ValueError(
                f"unsupported backend target: {request.target.backend_id} "
                f"(schema {request.architecture_schema})"
            )
        # Technology-specific interpretation stays here. The architecture
        # request itself remains unchanged and is never mutated by the backend.
        genome = Genome(dict(request.architecture))
        return CompiledArtifact(
            backend_id=self.target.backend_id,
            files=self._architecture_files(genome),
            metadata={
                "language": self.target.language,
                "framework": self.target.framework,
                "architecture_schema": request.architecture_schema,
            },
        )



class GoHTTPBackend:
    """Independent Go/net/http target used to prove backend neutrality."""

    target = BackendTarget(
        backend_id="go-nethttp",
        language="go",
        framework="net/http",
    )
    runtime_supported = False

    def supports(self, request: CompilationRequest) -> bool:
        return request.target == self.target and request.architecture_schema == ARCHITECTURE_SCHEMA_VERSION

    def compile(self, request: CompilationRequest) -> CompiledArtifact:
        if not self.supports(request):
            raise ValueError(
                f"unsupported backend target: {request.target.backend_id} "
                f"(schema {request.architecture_schema})"
            )
        genome = Genome(dict(request.architecture))
        plan = plan_capabilities(genome)
        # This backend intentionally proves a distinct lowering surface. It only
        # accepts capabilities whose semantics can be represented faithfully by
        # the small reference HTTP target; unsupported semantics remain explicit.
        allowed = {"services", "database", "authentication", "cors", "health_endpoints", "openapi", "api_version"}
        unsupported = set(plan.requested) - allowed
        if unsupported:
            raise ValueError("cannot lower unmapped capabilities for go-nethttp: " + ", ".join(sorted(unsupported)))
        if plan.requires("database") and genome.database not in {"sqlite"}:
            raise ValueError(
                f"database={genome.database!r} is not lowerable by go-nethttp: "
                "only sqlite is realized by the reference Go target"
            )
        if plan.requires("authentication") and genome.auth not in {"jwt", "api_key", "basic"}:
            raise ValueError(
                f"authentication={genome.auth!r} is not lowerable by go-nethttp: "
                "only jwt, api_key and basic are realized by the reference Go target"
            )
        main = self._generate_main(genome)
        go_mod = (
            "module generated-api\n\n"
            "go 1.22\n\n"
            "require modernc.org/sqlite v1.33.1\n"
        )
        return CompiledArtifact(
            backend_id=self.target.backend_id,
            files={"go.mod": go_mod, "main.go": main},
            metadata={"language": "go", "framework": "net/http", "architecture_schema": request.architecture_schema},
        )

    @staticmethod
    def _generate_main(genome: Genome) -> str:
        """Lower the architecture into an executable Go/net/http program."""
        api_version = genome.api_version
        services_json = "[]string{" + ", ".join(json.dumps(s) for s in genome.services) + "}"
        version_json = json.dumps(api_version)

        imports = ['"database/sql"', '"encoding/json"', '"log"', '"net/http"', '"os"']
        if genome.auth == "api_key":
            imports.append('"crypto/hmac"')
        elif genome.auth == "basic":
            imports.extend(['"crypto/hmac"', '"encoding/base64"', '"strings"'])
        else:  # jwt
            imports.extend(
                ['"crypto/hmac"', '"crypto/sha256"', '"encoding/base64"', '"fmt"', '"strings"', '"time"']
            )
        imports.append('_ "modernc.org/sqlite"')
        for index, module in enumerate(imports):
            imports[index] = "\t" + module
        import_block = "import (\n" + "\n".join(imports) + "\n)"

        auth_func = {
            "api_key": GoHTTPBackend._AUTH_API_KEY,
            "basic": GoHTTPBackend._AUTH_BASIC,
            "jwt": GoHTTPBackend._AUTH_JWT,
        }[genome.auth]

        cors_block = GoHTTPBackend._CORS_MIDDLEWARE if genome.cors_enabled else ""

        openapi_json = GoHTTPBackend._openapi_document(genome)
        openapi_block = (
            f"const openAPIDoc = `{openapi_json}`\n\n"
            "func openAPIHandler(w http.ResponseWriter, r *http.Request) {\n"
            '\tw.Header().Set("Content-Type", "application/json")\n'
            "\t_, _ = w.Write([]byte(openAPIDoc))\n"
            "}\n\n"
        )

        routes = "\n".join(
            f'\tmux.HandleFunc("{route}", requireAuth(serviceHandler(db, {json.dumps(service)})))'
            for service, route in (
                (service, f"/api/{api_version}/{service}") for service in genome.services
            )
        )

        listen_fatal = (
            'log.Fatal(http.ListenAndServe(":8000", withCORS(mux)))'
            if genome.cors_enabled
            else 'log.Fatal(http.ListenAndServe(":8000", mux))'
        )

        create_sql = _SQL_CREATE_RECORDS
        select_sql = _SQL_SELECT_RECORDS
        insert_sql = _SQL_INSERT_RECORDS

        return f'''package main

{import_block}

func writeJSON(w http.ResponseWriter, status int, value any) {{
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    _ = json.NewEncoder(w).Encode(value)
}}

func initDB() (*sql.DB, error) {{
    dsn := os.Getenv("DATABASE_URL")
    if dsn == "" {{
        dsn = "generated.db"
    }}
    db, err := sql.Open("sqlite", dsn)
    if err != nil {{
        return nil, err
    }}
    if err := db.Ping(); err != nil {{
        return nil, err
    }}
    create := `{create_sql}`
    if _, err := db.Exec(create); err != nil {{
        return nil, err
    }}
    return db, nil
}}

func serviceHandler(db *sql.DB, service string) http.HandlerFunc {{
    return func(w http.ResponseWriter, r *http.Request) {{
        switch r.Method {{
        case http.MethodGet:
            rows, err := db.Query("{select_sql}", service)
            if err != nil {{
                writeJSON(w, http.StatusInternalServerError, map[string]any{{"error": "query failed"}})
                return
            }}
            defer rows.Close()
            items := []any{{}}
            for rows.Next() {{
                var id int64
                var payload string
                if err := rows.Scan(&id, &payload); err != nil {{
                    continue
                }}
                var body map[string]any
                if json.Unmarshal([]byte(payload), &body) == nil {{
                    items = append(items, body)
                }}
            }}
            writeJSON(w, http.StatusOK, map[string]any{{"service": service, "items": items}})
        case http.MethodPost:
            var body map[string]any
            if err := json.NewDecoder(r.Body).Decode(&body); err != nil {{
                writeJSON(w, http.StatusBadRequest, map[string]any{{"error": "invalid request body"}})
                return
            }}
            payload, err := json.Marshal(body)
            if err != nil {{
                writeJSON(w, http.StatusBadRequest, map[string]any{{"error": "invalid request body"}})
                return
            }}
            if _, err := db.Exec("{insert_sql}", service, string(payload)); err != nil {{
                writeJSON(w, http.StatusInternalServerError, map[string]any{{"error": "insert failed"}})
                return
            }}
            writeJSON(w, http.StatusCreated, map[string]any{{"service": service, "created": body}})
        default:
            writeJSON(w, http.StatusMethodNotAllowed, map[string]any{{"error": "method not allowed"}})
        }}
    }}
}}

{auth_func}

{cors_block}
{openapi_block}func main() {{
    db, err := initDB()
    if err != nil {{
        log.Fatalf("database init failed: %v", err)
    }}
    defer db.Close()

    mux := http.NewServeMux()
    mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {{
        writeJSON(w, http.StatusOK, map[string]any{{"version": {version_json}, "services": {services_json}}})
    }})
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {{
        if err := db.Ping(); err != nil {{
            writeJSON(w, http.StatusServiceUnavailable, map[string]string{{"status": "unhealthy"}})
            return
        }}
        writeJSON(w, http.StatusOK, map[string]string{{"status": "healthy"}})
    }})
    mux.HandleFunc("/openapi.json", openAPIHandler)
{routes}
    {listen_fatal}
}}
'''

    _AUTH_API_KEY = """func requireAuth(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        expected := os.Getenv("API_KEY")
        if expected == "" {
            writeJSON(w, http.StatusInternalServerError, map[string]any{"error": "API_KEY is not configured"})
            return
        }
        if !hmac.Equal([]byte(r.Header.Get("X-API-Key")), []byte(expected)) {
            writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "invalid or missing API key"})
            return
        }
        next(w, r)
    }
}

"""

    _AUTH_BASIC = """func requireAuth(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        user := os.Getenv("BASIC_AUTH_USER")
        if user == "" {
            writeJSON(w, http.StatusInternalServerError, map[string]any{"error": "BASIC_AUTH_USER is not configured"})
            return
        }
        pass := os.Getenv("BASIC_AUTH_PASS")
        if pass == "" {
            writeJSON(w, http.StatusInternalServerError, map[string]any{"error": "BASIC_AUTH_PASS is not configured"})
            return
        }
        header := r.Header.Get("Authorization")
        const prefix = "Basic "
        if !strings.HasPrefix(header, prefix) {
            writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "missing basic credentials"})
            return
        }
        decoded, err := base64.StdEncoding.DecodeString(strings.TrimPrefix(header, prefix))
        if err != nil {
            writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "malformed basic credentials"})
            return
        }
        if !hmac.Equal(decoded, []byte(user+":"+pass)) {
            writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "invalid basic credentials"})
            return
        }
        next(w, r)
    }
}

"""

    _AUTH_JWT = """func verifyJWT(token string) (bool, error) {
    if token == "" {
        return false, fmt.Errorf("missing token")
    }
    secret := os.Getenv("JWT_SECRET")
    if secret == "" {
        return false, fmt.Errorf("JWT_SECRET is not configured")
    }
    parts := strings.Split(token, ".")
    if len(parts) != 3 {
        return false, fmt.Errorf("malformed token")
    }
    signingInput := parts[0] + "." + parts[1]
    mac := hmac.New(sha256.New, []byte(secret))
    mac.Write([]byte(signingInput))
    signature, err := base64.RawURLEncoding.DecodeString(parts[2])
    if err != nil || !hmac.Equal(signature, mac.Sum(nil)) {
        return false, fmt.Errorf("invalid signature")
    }
    payload, err := base64.RawURLEncoding.DecodeString(parts[1])
    if err != nil {
        return false, fmt.Errorf("invalid payload")
    }
    var claims struct {
        Exp int64 `json:"exp"`
    }
    if err := json.Unmarshal(payload, &claims); err != nil {
        return false, fmt.Errorf("invalid claims")
    }
    if claims.Exp != 0 && time.Now().Unix() > claims.Exp {
        return false, fmt.Errorf("token expired")
    }
    return true, nil
}

func requireAuth(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        header := r.Header.Get("Authorization")
        const prefix = "Bearer "
        if !strings.HasPrefix(header, prefix) {
            writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "missing bearer token"})
            return
        }
        ok, err := verifyJWT(strings.TrimPrefix(header, prefix))
        if err != nil || !ok {
            writeJSON(w, http.StatusUnauthorized, map[string]any{"error": "invalid token"})
            return
        }
        next(w, r)
    }
}

"""

    _CORS_MIDDLEWARE = """func withCORS(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Access-Control-Allow-Origin", "*")
        w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")
        if r.Method == http.MethodOptions {
            w.WriteHeader(http.StatusNoContent)
            return
        }
        next.ServeHTTP(w, r)
    })
}

"""

    @staticmethod
    def _openapi_document(genome: Genome) -> str:
        """Serialize a real OpenAPI 3.0 document for the lowered architecture."""
        security_scheme = {
            "api_key": {
                "apikey_auth": {"type": "apiKey", "name": "X-API-Key", "in": "header"},
            },
            "basic": {
                "basic_auth": {"type": "http", "scheme": "basic"},
            },
            "jwt": {
                "bearer_auth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            },
        }[genome.auth]
        paths = {
            f"/api/{genome.api_version}/{service}": {
                "get": {
                    "summary": f"List records for {service}",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "summary": f"Create a record for {service}",
                    "responses": {"201": {"description": "Created"}},
                },
            }
            for service in genome.services
        }
        paths["/health"] = {
            "get": {"summary": "Readiness probe", "responses": {"200": {"description": "OK"}}}
        }
        paths["/openapi.json"] = {
            "get": {"summary": "OpenAPI document", "responses": {"200": {"description": "OK"}}}
        }
        document = {
            "openapi": "3.0.0",
            "info": {
                "title": "Generated API",
                "version": genome.api_version,
            },
            "servers": [{"url": "/"}],
            "paths": paths,
            "components": {"securitySchemes": security_scheme},
            "security": [{next(iter(security_scheme)): []}],
        }
        return json.dumps(document, sort_keys=True)


_BACKENDS: Dict[str, CompilerBackend] = {
    PYTHON_FASTAPI.backend_id: PythonFastAPIBackend(),
    GoHTTPBackend.target.backend_id: GoHTTPBackend(),
}


def get_backend(backend_id: str) -> CompilerBackend:
    """Resolve an explicitly selected compiler backend; fail closed otherwise."""

    try:
        return _BACKENDS[backend_id]
    except KeyError as exc:
        raise ValueError(f"unknown compiler backend: {backend_id}") from exc


def compile_architecture(request: CompilationRequest) -> CompiledArtifact:
    """Compile using only the backend explicitly present in the request."""

    artifact = get_backend(request.target.backend_id).compile(request)
    architecture_payload = json.dumps(
        dict(request.architecture), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    metadata = dict(artifact.metadata)
    metadata["architecture_hash"] = hashlib.sha256(architecture_payload).hexdigest()
    metadata.setdefault("backend_id", artifact.backend_id)
    return CompiledArtifact(
        backend_id=artifact.backend_id,
        files=artifact.files,
        metadata=metadata,
    )


def materialize(artifact: CompiledArtifact, output_dir: str) -> str:
    """Write an artifact safely and persist a content-addressed manifest."""
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    file_digests: Dict[str, str] = {}
    for relative_path, content in artifact.files.items():
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"artifact path escapes output directory: {relative_path!r}")
        full_path = (root / relative).resolve()
        if root != full_path and root not in full_path.parents:
            raise ValueError(f"artifact path escapes output directory: {relative_path!r}")
        full_path.parent.mkdir(parents=True, exist_ok=True)
        data = content.encode("utf-8")
        full_path.write_bytes(data)
        file_digests[relative.as_posix()] = hashlib.sha256(data).hexdigest()

    if "go.mod" in artifact.files:
        # Resolve the module graph before content-addressing so a later
        # `go build` cannot mutate go.mod/go.sum after digests are recorded.
        try:
            subprocess.run(
                ["go", "mod", "tidy"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        file_digests = {}
        for relative_path in artifact.files:
            full_path = root / relative_path
            if full_path.is_file():
                file_digests[Path(relative_path).as_posix()] = hashlib.sha256(
                    full_path.read_bytes()
                ).hexdigest()
        go_sum = root / "go.sum"
        if go_sum.is_file():
            file_digests["go.sum"] = hashlib.sha256(go_sum.read_bytes()).hexdigest()

    manifest_payload = {
        "manifest_version": 1,
        "backend_id": artifact.backend_id,
        "architecture_hash": artifact.metadata.get("architecture_hash"),
        "files": dict(sorted(file_digests.items())),
    }
    manifest_bytes = json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_payload["artifact_digest"] = hashlib.sha256(manifest_bytes).hexdigest()
    (root / "artifact-manifest.json").write_text(
        json.dumps(manifest_payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return str(root)



def _validate_verified_artifact(source_dir: str, expected_digest: str) -> dict:
    """Validate a content-addressed artifact and return its manifest."""
    source = Path(source_dir).resolve()
    manifest_path = source / "artifact-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("verified artifact is missing artifact-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("artifact_digest") != expected_digest:
        raise ValueError("verified artifact digest does not match expected digest")
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ValueError("artifact manifest has no file digest map")
    digest_payload = {
        "manifest_version": manifest.get("manifest_version"),
        "backend_id": manifest.get("backend_id"),
        "architecture_hash": manifest.get("architecture_hash"),
        "files": dict(sorted(files.items())),
    }
    calculated_digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if calculated_digest != expected_digest:
        raise ValueError("verified artifact manifest digest verification failed")
    for relative_path, expected_file_digest in files.items():
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"manifest path escapes artifact root: {relative_path!r}")
        file_path = (source / relative).resolve()
        if source != file_path and source not in file_path.parents:
            raise ValueError(f"manifest path escapes artifact root: {relative_path!r}")
        if not file_path.is_file():
            raise ValueError(f"manifest file is missing: {relative_path!r}")
        actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual != expected_file_digest:
            raise ValueError(f"artifact file digest mismatch: {relative_path!r}")
    return manifest


def _copy_verified_tree(source: Path, destination: Path, manifest: dict) -> None:
    import shutil
    for relative_path in manifest["files"]:
        relative = Path(relative_path)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    (destination / "artifact-manifest.json").write_text(
        (source / "artifact-manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def backup_verified_artifact(source_dir: str, backup_dir: str, *, expected_digest: str) -> str:
    """Create a durable, digest-verified backup of a known-good artifact."""
    source = Path(source_dir).resolve()
    backup = Path(backup_dir).resolve()
    manifest = _validate_verified_artifact(str(source), expected_digest)
    import shutil
    import tempfile
    backup.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{backup.name}.", dir=str(backup.parent)))
    try:
        _copy_verified_tree(source, staging, manifest)
        for relative_path, expected_file_digest in manifest["files"].items():
            actual = hashlib.sha256((staging / relative_path).read_bytes()).hexdigest()
            if actual != expected_file_digest:
                raise ValueError(f"backup artifact file digest mismatch: {relative_path!r}")
        if backup.exists():
            shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
        staging.rename(backup)
        return str(backup)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def restore_verified_artifact(backup_dir: str, destination_dir: str, *, expected_digest: str) -> str:
    """Restore a durable backup only when its content digest is verified."""
    backup = Path(backup_dir).resolve()
    destination = Path(destination_dir).resolve()
    manifest = _validate_verified_artifact(str(backup), expected_digest)
    import shutil
    import tempfile
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.restore-", dir=str(destination.parent)))
    previous = destination.with_name(f".{destination.name}.restore-previous")
    try:
        _copy_verified_tree(backup, staging, manifest)
        for relative_path, expected_file_digest in manifest["files"].items():
            actual = hashlib.sha256((staging / relative_path).read_bytes()).hexdigest()
            if actual != expected_file_digest:
                raise ValueError(f"restored artifact file digest mismatch: {relative_path!r}")
        if previous.exists():
            shutil.rmtree(previous) if previous.is_dir() else previous.unlink()
        if destination.exists():
            destination.rename(previous)
        staging.rename(destination)
        if previous.exists():
            shutil.rmtree(previous)
        return str(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        if not destination.exists() and previous.exists():
            previous.rename(destination)
        raise

def promote_verified_artifact(source_dir: str, destination_dir: str, *, expected_digest: str) -> str:
    """Promote the exact verified artifact after validating its content digest."""
    source = Path(source_dir).resolve()
    destination = Path(destination_dir).resolve()
    manifest = _validate_verified_artifact(str(source), expected_digest)
    files = manifest["files"]

    import shutil
    import tempfile

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=str(destination.parent)))
    backup = destination.with_name(f".{destination.name}.previous")
    try:
        for relative_path in files:
            relative = Path(relative_path)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target)
        (staging / "artifact-manifest.json").write_text(
            (source / "artifact-manifest.json").read_text(encoding="utf-8"), encoding="utf-8"
        )

        # Revalidate the complete staged tree before exposing it.
        for relative_path, expected_file_digest in files.items():
            actual = hashlib.sha256((staging / relative_path).read_bytes()).hexdigest()
            if actual != expected_file_digest:
                raise ValueError(f"staged artifact file digest mismatch: {relative_path!r}")

        if backup.exists():
            shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
        if destination.exists():
            destination.rename(backup)
        staging.rename(destination)
        # Preserve the verified previous artifact as the durable rollback point.
        return str(destination)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        if not destination.exists() and backup.exists():
            backup.rename(destination)
        raise


def compile_and_materialize(
    architecture: Dict[str, object],
    output_dir: str,
    target: BackendTarget = PYTHON_FASTAPI,
) -> str:
    """Compile an architecture through the registry and persist the artifact."""

    artifact = compile_architecture(make_compilation_request(architecture, target=target))
    return materialize(artifact, output_dir)
