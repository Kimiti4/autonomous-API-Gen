from app.engine.genome import Genome


SUPPORTED_AUTH = {"jwt", "api_key", "basic"}


def generate_main_app(genome: Genome) -> str:
    services_imports = "\n".join(f"from services.{svc} import router as {svc}_router" for svc in genome.services)
    services_includes = "\n".join(f'app.include_router({svc}_router, prefix="/api/{genome.api_version}/{svc}", tags=["{svc}"])' for svc in genome.services)
    cors_code = """
from fastapi.middleware.cors import CORSMiddleware
_allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_allowed_origins, allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-API-Key"])
""" if genome.cors_enabled else ""
    rate_limit_code = """
from collections import defaultdict, deque
from time import monotonic
from fastapi import Request
from fastapi.responses import JSONResponse
_RATE_LIMIT_WINDOW = 60.0
_RATE_LIMIT_MAX = max(1, int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60")))
_rate_limit_hits = defaultdict(deque)
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)
    now = monotonic()
    key = request.client.host if request.client else "unknown"
    hits = _rate_limit_hits[key]
    while hits and now - hits[0] >= _RATE_LIMIT_WINDOW:
        hits.popleft()
    if len(hits) >= _RATE_LIMIT_MAX:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    hits.append(now)
    return await call_next(request)
""" if genome.rate_limiting else ""
    metrics_code = """
from collections import Counter
_metrics_requests = Counter()
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    response = await call_next(request)
    _metrics_requests[(request.method, request.url.path, response.status_code)] += 1
    return response
@app.get("/metrics")
async def metrics():
    lines = ["# HELP http_requests_total Total HTTP requests", "# TYPE http_requests_total counter"]
    for (method, path, status), count in sorted(_metrics_requests.items()):
        safe_path = path.replace('\\"', '\\\\"')
        lines.append(f'http_requests_total{{method="{method}",path="{safe_path}",status="{status}"}} {count}')
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("\\n".join(lines) + "\\n", media_type="text/plain; version=0.0.4")
""" if genome.metrics_endpoints else ""
    tracing_code = """
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
_tracer_provider = TracerProvider(resource=Resource.create({"service.name": "evolved-api"}))
_tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(_tracer_provider)
_tracer = trace.get_tracer("evolved-api")
""" if genome.tracing_enabled else ""
    otel_middleware_code = """
app.add_middleware(OpenTelemetryMiddleware, excluded_urls="metrics")
""" if genome.tracing_enabled else ""
    tracing_probe_code = """
@app.middleware("http")
async def tracing_probe_middleware(request: Request, call_next):
    response = await call_next(request)
    span = trace.get_current_span()
    context = span.get_span_context()
    if context.is_valid:
        response.headers["X-Trace-ID"] = format(context.trace_id, "032x")
    return response
""" if genome.tracing_enabled else ""
    timeout_code = ""
    if genome.timeout_config:
        timeout_value = float(genome.timeout_config.get("request_timeout", 0))
        if timeout_value <= 0:
            raise ValueError("timeout_config.request_timeout must be greater than zero")
        timeout_code = f"""
import asyncio
from fastapi.responses import JSONResponse
REQUEST_TIMEOUT_SECONDS = {timeout_value!r}
@app.middleware("http")
async def request_timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={{"detail": "Request timed out"}})
@app.get("/__capability_probe__/timeout")
async def timeout_capability_probe():
    if os.getenv("CAPABILITY_EVIDENCE_MODE") != "1":
        return JSONResponse(status_code=404, content={{"detail": "Not found"}})
    await asyncio.sleep(REQUEST_TIMEOUT_SECONDS * 2)
    return {{"completed": True}}
"""
    retry_code = ""
    if genome.retry_policy:
        retry = genome.retry_policy
        max_attempts = int(retry.get("max_attempts", 0))
        base_delay = float(retry.get("base_delay", 0))
        max_delay = float(retry.get("max_delay", 0))
        multiplier = float(retry.get("backoff_multiplier", 0))
        if max_attempts < 2 or base_delay < 0 or max_delay < base_delay or multiplier < 1:
            raise ValueError("retry_policy requires max_attempts >= 2, base_delay >= 0, max_delay >= base_delay, and backoff_multiplier >= 1")
        retry_code = f"""
import asyncio
from fastapi.responses import JSONResponse
RETRY_MAX_ATTEMPTS = {max_attempts!r}
RETRY_BASE_DELAY = {base_delay!r}
RETRY_MAX_DELAY = {max_delay!r}
RETRY_BACKOFF_MULTIPLIER = {multiplier!r}
RETRYABLE_STATUS_CODES = frozenset({{502, 503, 504}})
class RetryPolicyMiddleware:
    def __init__(self, app: object) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: object, send: object) -> None:
        if scope.get("type") != "http" or scope.get("method") not in {{"GET", "HEAD", "OPTIONS"}}:
            await self.app(scope, receive, send)
            return
        chunks = []
        more_body = True
        while more_body:
            message = await receive()
            if message.get("type") != "http.request":
                break
            chunks.append(message.get("body", b""))
            more_body = message.get("more_body", False)
        body = b"".join(chunks)

        async def replay_receive():
            yield {{"type": "http.request", "body": body, "more_body": False}}
            yield {{"type": "http.disconnect"}}

        delay = RETRY_BASE_DELAY
        for attempt in range(RETRY_MAX_ATTEMPTS):
            state = {{"status": 0, "headers": [], "body": bytearray()}}

            async def capture_send(message):
                if message.get("type") == "http.response.start":
                    state["status"] = message.get("status", 0)
                    state["headers"] = message.get("headers", [])
                elif message.get("type") == "http.response.body":
                    state["body"] += message.get("body", b"")

            await self.app(dict(scope), replay_receive().__aiter__().__anext__, capture_send)
            if state["status"] not in RETRYABLE_STATUS_CODES or attempt == RETRY_MAX_ATTEMPTS - 1:
                break
            if delay > 0:
                await asyncio.sleep(min(delay, RETRY_MAX_DELAY))
                delay = min(delay * RETRY_BACKOFF_MULTIPLIER, RETRY_MAX_DELAY)

        await send({{"type": "http.response.start", "status": state["status"], "headers": state["headers"]}})
        await send({{"type": "http.response.body", "body": bytes(state["body"]), "more_body": False}})
app.add_middleware(RetryPolicyMiddleware)
_retry_probe_attempts = 0
@app.get("/__capability_probe__/retry")
async def retry_capability_probe():
    global _retry_probe_attempts
    if os.getenv("CAPABILITY_EVIDENCE_MODE") != "1":
        return JSONResponse(status_code=404, content={{"detail": "Not found"}})
    _retry_probe_attempts += 1
    if _retry_probe_attempts < 2:
        return JSONResponse(status_code=503, content={{"detail": "transient failure"}})
    return {{"attempts": _retry_probe_attempts}}
"""
    circuit_breaker_code = ""
    if genome.circuit_breaker:
        circuit_breaker_code = """
import asyncio
from time import monotonic
from fastapi.responses import JSONResponse
CIRCUIT_FAILURE_THRESHOLD = 2
CIRCUIT_COOLDOWN_SECONDS = 0.10
CIRCUIT_TRANSIENT_STATUS_CODES = frozenset({502, 503, 504})
class CircuitBreakerMiddleware:
    def __init__(self, app: object) -> None:
        self.app = app
        self.state = "CLOSED"
        self.failures = 0
        self.opened_at = 0.0
        self.half_open_in_flight = False
        self.lock = asyncio.Lock()

    async def __call__(self, scope: dict, receive: object, send: object) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        now = monotonic()
        async with self.lock:
            if self.state == "OPEN":
                if now - self.opened_at < CIRCUIT_COOLDOWN_SECONDS:
                    await send({"type": "http.response.start", "status": 503,
                                "headers": [(b"content-type", b"application/json"),
                                             (b"retry-after", b"1")]})
                    await send({"type": "http.response.body", "body": b'{"detail":"Circuit open"}', "more_body": False})
                    return
                self.state = "HALF_OPEN"
                self.half_open_in_flight = True
            elif self.state == "HALF_OPEN":
                await send({"type": "http.response.start", "status": 503,
                            "headers": [(b"content-type", b"application/json"),
                                         (b"retry-after", b"1")]})
                await send({"type": "http.response.body", "body": b'{"detail":"Circuit open"}', "more_body": False})
                return

        state = {"status": 0, "headers": [], "body": bytearray()}
        async def capture_send(message):
            if message.get("type") == "http.response.start":
                state["status"] = message.get("status", 0)
                state["headers"] = message.get("headers", [])
            elif message.get("type") == "http.response.body":
                state["body"] += message.get("body", b"")

        await self.app(scope, receive, capture_send)
        async with self.lock:
            if state["status"] in CIRCUIT_TRANSIENT_STATUS_CODES:
                self.failures += 1
                if self.failures >= CIRCUIT_FAILURE_THRESHOLD:
                    self.state = "OPEN"
                    self.opened_at = monotonic()
                elif self.state == "HALF_OPEN":
                    self.state = "OPEN"
                    self.opened_at = monotonic()
                self.half_open_in_flight = False
            elif 200 <= state["status"] < 500:
                self.failures = 0
                self.state = "CLOSED"
                self.half_open_in_flight = False
            elif self.state == "HALF_OPEN":
                self.state = "OPEN"
                self.opened_at = monotonic()
                self.half_open_in_flight = False
        await send({"type": "http.response.start", "status": state["status"], "headers": state["headers"]})
        await send({"type": "http.response.body", "body": bytes(state["body"]), "more_body": False})
app.add_middleware(CircuitBreakerMiddleware)
_circuit_probe_attempts = 0
@app.get("/__capability_probe__/circuit-breaker")
async def circuit_breaker_capability_probe():
    global _circuit_probe_attempts
    if os.getenv("CAPABILITY_EVIDENCE_MODE") != "1":
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    _circuit_probe_attempts += 1
    if _circuit_probe_attempts <= CIRCUIT_FAILURE_THRESHOLD:
        return JSONResponse(status_code=503, content={"attempts": _circuit_probe_attempts})
    return {"attempts": _circuit_probe_attempts, "recovered": True}
"""
    cache_code = ""
    if genome.cache_enabled:
        cache_code = """
from collections import OrderedDict
from hashlib import sha256
from time import monotonic
from fastapi.responses import Response
CACHE_TTL_SECONDS = max(0.0, float(os.getenv("CACHE_TTL_SECONDS", "30")))
CACHE_MAX_ENTRIES = max(1, int(os.getenv("CACHE_MAX_ENTRIES", "256")))
_cache_store = OrderedDict()
_cache_lock = asyncio.Lock()

def _cache_key(scope):
    query = scope.get("query_string", b"").decode("utf-8", errors="replace")
    headers = {k.lower(): v for k, v in scope.get("headers", [])}
    identity = headers.get(b"authorization", b"") or headers.get(b"x-api-key", b"")
    identity_hash = sha256(identity).hexdigest() if identity else "anonymous"
    return (scope.get("method"), scope.get("path"), query, identity_hash)

class ResponseCacheMiddleware:
    def __init__(self, app: object) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: object, send: object) -> None:
        method = scope.get("method")
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            async with _cache_lock:
                _cache_store.clear()
            await self.app(scope, receive, send)
            return
        if method not in {"GET", "HEAD"}:
            await self.app(scope, receive, send)
            return
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        if headers.get(b"authorization") or headers.get(b"x-api-key"):
            await self.app(scope, receive, send)
            return
        key = _cache_key(scope)
        now = monotonic()
        async with _cache_lock:
            entry = _cache_store.get(key)
            if entry and now - entry["created_at"] < CACHE_TTL_SECONDS:
                _cache_store.move_to_end(key)
                await send({"type": "http.response.start", "status": entry["status"], "headers": entry["headers"]})
                await send({"type": "http.response.body", "body": entry["body"], "more_body": False})
                return
            if entry:
                _cache_store.pop(key, None)

        state = {"status": 0, "headers": [], "body": bytearray()}
        async def capture_send(message):
            if message.get("type") == "http.response.start":
                state["status"] = message.get("status", 0)
                state["headers"] = message.get("headers", [])
            elif message.get("type") == "http.response.body":
                state["body"] += message.get("body", b"")
        await self.app(scope, receive, capture_send)
        if state["status"] == 200:
            async with _cache_lock:
                _cache_store[key] = {"created_at": monotonic(), "status": state["status"], "headers": state["headers"], "body": bytes(state["body"])}
                _cache_store.move_to_end(key)
                while len(_cache_store) > CACHE_MAX_ENTRIES:
                    _cache_store.popitem(last=False)
        await send({"type": "http.response.start", "status": state["status"], "headers": state["headers"]})
        await send({"type": "http.response.body", "body": bytes(state["body"]), "more_body": False})
app.add_middleware(ResponseCacheMiddleware)
_cache_probe_hits = 0
@app.get("/__capability_probe__/cache")
async def cache_capability_probe():
    global _cache_probe_hits
    if os.getenv("CAPABILITY_EVIDENCE_MODE") != "1":
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    _cache_probe_hits += 1
    return {"handler_hits": _cache_probe_hits}
@app.post("/__capability_probe__/cache/invalidate")
async def cache_invalidation_probe():
    if os.getenv("CAPABILITY_EVIDENCE_MODE") != "1":
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return {"invalidated": True}
"""
    health_code = '''
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
''' if genome.health_endpoints else ""
    logging_code = ""
    if genome.logging_level:
        import_level = genome.logging_level
        logging_code = f"""
import logging
logging.basicConfig(level=logging.{import_level}, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("generated-api")
"""
    request_import = "from fastapi import Request\n" if genome.metrics_endpoints or genome.rate_limiting or genome.tracing_enabled or genome.timeout_config or genome.retry_policy or genome.cache_enabled else ""
    return f'''"""Generated API architecture."""
import os
import asyncio
from fastapi import FastAPI
{request_import}{services_imports}
{logging_code}
from database import init_db
app = FastAPI(title="Evolved API System", version="{genome.api_version}", description="Generated API architecture")
{cors_code}
{tracing_code}
{tracing_probe_code}
{rate_limit_code}
{metrics_code}
{timeout_code}
{retry_code}
{circuit_breaker_code}
{cache_code}
{otel_middleware_code if genome.tracing_enabled else ""}
{services_includes}
@app.get("/")
async def root():
    return {{"message": "Evolved API System", "version": "{genome.api_version}", "services": {genome.services}}}
{health_code}
@app.on_event("startup")
async def startup():
    init_db()
'''


def generate_database_file(genome: Genome) -> str:
    defaults = {"sqlite": "sqlite:///./generated.db", "mysql": "mysql+pymysql://user:password@localhost/app", "postgres": "postgresql+psycopg2://user:password@localhost/app"}
    connect_args = '{"check_same_thread": False}' if genome.database == "sqlite" else "{}"
    return f'''import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
DATABASE_URL = os.getenv("DATABASE_URL", "{defaults[genome.database]}")
engine = create_engine(DATABASE_URL, connect_args={connect_args}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
def init_db():
    from services import models
    Base.metadata.create_all(bind=engine)
'''


def generate_security_file(genome: Genome) -> str:
    if genome.auth not in SUPPORTED_AUTH:
        raise ValueError(f"Unsupported authentication capability: {genome.auth}")
    return '''import os
import hmac
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer, HTTPBasic, HTTPBasicCredentials
AUTH_MODE = os.getenv("AUTH_MODE", "''' + genome.auth + '''")
API_KEY = os.getenv("API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
BASIC_USER = os.getenv("BASIC_USER")
BASIC_PASSWORD = os.getenv("BASIC_PASSWORD")
bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
basic = HTTPBasic(auto_error=False)
def require_auth(credentials: HTTPAuthorizationCredentials = Depends(bearer), api_key: str | None = Depends(api_key_header), basic_credentials: HTTPBasicCredentials | None = Depends(basic)):
    if AUTH_MODE == "api_key":
        if API_KEY and api_key and hmac.compare_digest(api_key, API_KEY): return "api-key"
        raise HTTPException(status_code=401, detail="Authentication required")
    if AUTH_MODE == "jwt":
        if not credentials or not JWT_SECRET: raise HTTPException(status_code=401, detail="Authentication required")
        try:
            import jwt
            jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
            return "bearer"
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
    if AUTH_MODE == "basic":
        if not basic_credentials or not BASIC_USER or not BASIC_PASSWORD: raise HTTPException(status_code=401, detail="Authentication required")
        if hmac.compare_digest(basic_credentials.username, BASIC_USER) and hmac.compare_digest(basic_credentials.password, BASIC_PASSWORD): return basic_credentials.username
        raise HTTPException(status_code=401, detail="Invalid credentials", headers={"WWW-Authenticate": "Basic"})
    raise HTTPException(status_code=500, detail="Unsupported authentication mode")
'''


def generate_models_file(genome: Genome) -> str:
    models = ['from sqlalchemy import Column, Integer, String, Text\nfrom database import Base\n']
    for service in genome.services:
        models.append(f'''class {service.capitalize()}Item(Base):
    __tablename__ = "{service}_items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
''')
    return "\n".join(models)


def generate_service_file(service_name: str, genome: Genome) -> str:
    cls = service_name.capitalize()
    auth_import = "from security import require_auth\n" if genome.auth else ""
    auth_dep = "(dependencies=[Depends(require_auth)])" if genome.auth else ""
    return f'''from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import SessionLocal
from services.models import {cls}Item
{auth_import}
router = APIRouter{auth_dep}
class {cls}Payload(BaseModel):
    name: str
    description: str | None = None
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
@router.get("/")
def list_items(db: Session = Depends(get_db)):
    items = db.query({cls}Item).all()
    return {{"items": [{{"id": i.id, "name": i.name, "description": i.description}} for i in items]}}
@router.get("/{{item_id}}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get({cls}Item, item_id)
    if item is None: raise HTTPException(status_code=404, detail="Item not found")
    return {{"id": item.id, "name": item.name, "description": item.description}}
@router.post("/", status_code=201)
def create_item(payload: {cls}Payload, db: Session = Depends(get_db)):
    item = {cls}Item(name=payload.name, description=payload.description); db.add(item); db.commit(); db.refresh(item)
    return {{"id": item.id, "name": item.name, "description": item.description}}
@router.put("/{{item_id}}")
def update_item(item_id: int, payload: {cls}Payload, db: Session = Depends(get_db)):
    item = db.get({cls}Item, item_id)
    if item is None: raise HTTPException(status_code=404, detail="Item not found")
    item.name = payload.name; item.description = payload.description; db.commit(); db.refresh(item)
    return {{"id": item.id, "name": item.name, "description": item.description}}
@router.delete("/{{item_id}}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get({cls}Item, item_id)
    if item is None: raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item); db.commit()
'''


def generate_requirements(genome: Genome) -> str:
    packages = ["fastapi>=0.100.0", "uvicorn>=0.23.0", "pydantic>=2.0.0", "sqlalchemy>=2.0.0"]
    if genome.database == "postgres": packages.append("psycopg2-binary>=2.9.0")
    elif genome.database == "mysql": packages.append("pymysql>=1.0.0")
    if genome.auth == "jwt": packages.append("PyJWT>=2.8.0")
    if genome.tracing_enabled:
        packages.extend(["opentelemetry-api>=1.25.0", "opentelemetry-sdk>=1.25.0", "opentelemetry-instrumentation-asgi>=0.46b0"])
    return "\n".join(packages) + "\n"


def build_genome_output(genome: Genome, output_dir: str = "output/generated_api") -> str:
    # Committed Genome -> validated architecture request -> backend boundary.
    # The generator never interprets the architecture directly; lowering is a
    # compiler-backend concern (see app/engine/backends.py).
    from app.engine.backends import compile_and_materialize

    return compile_and_materialize(genome.encode(), output_dir=output_dir)


def generate_dockerfile(genome: Genome) -> str:
    return '''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]'''