"""Compiler backend registry.

The registry is deliberately small: backend selection is a compiler concern,
not a Genome concern. Additional language/framework targets can implement the
same CompilerBackend contract without changing the ISR-facing model.
"""

import os
import json
import hashlib
from typing import Dict

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
    create := `CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service TEXT NOT NULL,
        payload TEXT NOT NULL
    )`
    if _, err := db.Exec(create); err != nil {{
        return nil, err
    }}
    return db, nil
}}

func serviceHandler(db *sql.DB, service string) http.HandlerFunc {{
    return func(w http.ResponseWriter, r *http.Request) {{
        switch r.Method {{
        case http.MethodGet:
            rows, err := db.Query("SELECT id, payload FROM records WHERE service = ?", service)
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
            if _, err := db.Exec("INSERT INTO records (service, payload) VALUES (?, ?)", service, string(payload)); err != nil {{
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
            expected = "generated-api-key"
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
            user = "generated-user"
        }
        pass := os.Getenv("BASIC_AUTH_PASS")
        if pass == "" {
            pass = "generated-pass"
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
        secret = "generated-jwt-secret"
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
    metadata.setdefault(
        "architecture_hash",
        hashlib.sha256(architecture_payload).hexdigest(),
    )
    metadata.setdefault("backend_id", artifact.backend_id)
    return CompiledArtifact(
        backend_id=artifact.backend_id,
        files=artifact.files,
        metadata=metadata,
    )


def materialize(artifact: CompiledArtifact, output_dir: str) -> str:
    """Write a compiled artifact's file tree to disk without mutating it."""

    os.makedirs(output_dir, exist_ok=True)
    for relative_path, content in artifact.files.items():
        full_path = os.path.join(output_dir, relative_path)
        directory = os.path.dirname(full_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    return output_dir


def compile_and_materialize(
    architecture: Dict[str, object],
    output_dir: str,
    target: BackendTarget = PYTHON_FASTAPI,
) -> str:
    """Compile an architecture through the registry and persist the artifact."""

    artifact = compile_architecture(make_compilation_request(architecture, target=target))
    return materialize(artifact, output_dir)
