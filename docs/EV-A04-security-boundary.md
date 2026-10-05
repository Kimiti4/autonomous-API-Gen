# EV-A04 — Security Boundary

- **State audited:** `6e1aa1a` (PR #1 head), fetched tree clean; pending Bandit fix excluded from baseline (two-state discipline maintained).
- **Method:** READ-ONLY, NON-MUTATING, EVIDENCE-FIRST. Static tracing (`git show`/`git grep` at `6e1aa1a`) + two runtime probes outside the repo tree: in-process TestClient (`ev04_probe.py`, 32 records) and real uvicorn transport on `127.0.0.1:18765-18768` (`ev04_uvicorn*.py`, raw-socket WebSocket handshakes included). No mutating route was invoked (`/evolve/start`, `/evolve/sync`, `clear-memory` were probed **unauthenticated only** → 401); probe cwd = temp so `data/`+`logs/` never touched the repo. `git status` clean except this `docs/` series.
- **Taxonomy:** `IMPLEMENTED_REAL` / `IMPLEMENTED_BOUNDED` / `IMPLEMENTED_SIMULATED` / `PARTIAL` / `UNIMPLEMENTED` / `UNKNOWN`.
- **Confidence:** `CONFIRMED` / `INFERRED` / `UNVERIFIED`.
- **Scope boundary:** CI-integrity reds (EV-A01), artifact correctness (EV-A02), capability truthfulness (EV-A03) are not re-argued; only referenced where they cross the auth boundary (EV-A03-007).

---

## 0. STATUS

**STATUS: FAIL** — bounded to whether the advertised security boundary is what the platform actually enforces.

The **core key-auth design is real and fail-closed**: production refuses to start unconfigured (double gate), an unconfigured dev instance still 401s everything protected, `hmac.compare_digest` is used on every comparison, query-string tokens are rejected, the protected prefixes hold under path-confusion probes, and auth-before-accept holds on WebSocket. Those are genuine controls, all reproduced at runtime.

The failures are in **what the boundary does not cover, and in three advertised contracts that are false**:

1. **`GET /stream` is fully anonymous** — one request fans out to 3 agents × `call_llm` (60 s-timeout HTTP to a hardcoded Ollama URL) and streams the results, leaking `str(e)` from the LLM client. The prefix allow-list never covered it; nothing else did either. (§3)
2. **The advertised rate-limit control is broken end-to-end**: the limiter raises `HTTPException(429)` from *outside* `ExceptionMiddleware`, so clients receive **500 `PLATFORM_INTERNAL`** — no `Retry-After`, no `X-RateLimit-*`, and **no security headers at all** (the `server: uvicorn` header reappears). Tracked docs promise "21st+ request should return 429." Worse, the bucket is keyed per-IP but **counted before authentication**: 19 anonymous 401s exhaust it and a valid-key operator then gets the same 500 for the rest of the 60 s window — an anonymous, repeatable lockout of the authenticated control plane. (§4, §5)
3. **The WebSocket rejection contract is false on a real transport**: constitutional comment promises "close code 4401 with an ErrorEnvelope frame"; over uvicorn the client receives **`HTTP/1.1 403 Forbidden`, `Content-Length: 0`, empty body** — no code, no envelope. Enforcement (reject-before-accept) is real; the delivery claim only holds under TestClient semantics. (§7)

Plus: two divergent 401 shapes on the same platform (§4), five documented settings that are wired to nothing (§5), OpenAPI publishing **zero** security declarations across all 17 operations (§10), decorative `scopes` (§8), and a config-time CORS validator that accepts `http://localhost.evil.com` and any `https://` origin (§6).

This is the *companion* audit to EV-A03-007 (generated-artifact auth fail-open in Go): EV-A04 is the **platform's own** boundary; §9 carries the generated-artifact cross-ref forward without re-arguing it.

---

## 1. Boundary map — who protects what (at `6e1aa1a`)

| Surface | Route(s) | Guard | Runtime result (uvicorn/TestClient) |
|---|---|---|---|
| Root | `/` | none (by design) | 200, advertises `/docs` + `/ws/evolution` |
| Health | `/health` | none (by design) | 200 — leaks disk %, RSS/VMS MB, db status (§6) |
| Docs | `/docs`, `/redoc`, `/openapi.json` | none (enshrined by `test_docs_endpoint_accessible`) | 200 ×3 |
| **Inference SSE** | **`GET /stream`** | **none — no prefix, no dep** | **200 `text/event-stream`, 3 agents run (§3)** |
| Control plane | `/evolve*`, `/production/readiness*` | `PROTECTED_CONTROL_PREFIXES` in `SecurityHeadersMiddleware` pre-`call_next` (`security.py:24,31-45`) | 401 flat JSON — probed on `/evolve/runs`, `/evolve/start`, `/evolve/elite/start`, `/evolve/elite/clear-memory`, `/production/readiness` |
| Observation | `/observation/*` (5 routes) | per-route `_auth=Depends(require_auth)` (`observation_routes.py:113,125,132,142,163`) | 401 **full ErrorEnvelope** |
| WebSocket | `/ws/evolution`, `/ws/evolution/{run_id}` | auth **before** `accept` (`ws.py:87-94,100,128`) | real transport: **403 empty** (unauth) / 101 (authed) |
| Metrics | `/metrics` (prometheus instrumentator) | **no route-level auth** (instrumentator default path; registered via `setup_metrics`) | not probed — outside registered surface, flagged §12 |

Middleware stack (introspected): `[PrometheusInstrumentator, CORS, RateLimit, SecurityHeaders]` → `ExceptionMiddleware` → router. Order matters: **CORS outermost** (preflight short-circuits everything), **RateLimit outside SecurityHeaders** (counts before auth; its exceptions bypass both SecurityHeaders' `_secure()` and `ExceptionMiddleware`).

**Path-confusion probes (no bypass found):** `/evolvex` → 401 (prefix over-match, fail-closed), `/EVOLVE/runs` → 404 (case-sensitive router), `//evolve/runs` → 404 (prefix miss, but no route exists either), `/%65volve/runs` → 401 (ASGI decodes before the check — decode-then-check order is correct).

---

## 2. Authentication model — what is actually enforced (positives)

- **Provider:** `ApiKeyAuthProvider` only, registered iff `settings.ADMIN_API_KEY` (`main.py:31-35`); wrapped in `CompositeAuthProvider` (raises on empty list — can't construct a zero-provider composite, `security.py:151-153`).
- **Three channels, all CONFIRMED at runtime over uvicorn** (valid key → 200 `/evolve/runs`): `X-API-Key` header, `Authorization: Bearer`, **cookie `api_key`**. Wrong key → 401. `?api_key=` in the query string → **401** (claim "No bearer tokens in URLs" holds — `authenticate()` reads header/bearer/cookie only, `security.py:122-132`).
- **Fail-closed when unconfigured:** no `ADMIN_API_KEY` → `set_auth_provider` never called → `get_auth()` raises → middleware's `except Exception: ctx = None` → 401; route deps raise `UnauthenticatedError` → envelope 401. Reproduced by the tracked suite `autonomous-api/tests/observation/test_auth_fail_closed.py` (**7/7 passed** in this audit).
- **Production double gate:** `Settings._validate_production_security` (`config.py:57-66`: `ADMIN_API_KEY` required, `SECRET_KEY` not placeholder, `CORS_ORIGINS` non-empty) **and** `validate_auth_config` (`security.py:171-176` refuses to start with zero providers). Both `CONFIRMED` static.
- **Constant-time:** every secret comparison is `hmac.compare_digest` (`security.py:120`; generated code `builder.py:413,425`).
- **Auth-before-validation:** unauth `GET /observation/fitness?generation=-1` → **401**, not 422 — `require_auth` fires before query validation, so unauthenticated callers can't even probe the schema with invalid input. Authed → 422 envelope with **field names only, no value echo** (`error_handler.py:129`).
- **Auth-before-accept (WS):** enforced — raw handshake without credentials gets HTTP 403 (never upgraded). With key → 101. (Delivery of the *rejection reason* is §7.)

---

## 3. The anonymous surface — `/stream` (EV-A04-001)

```python
@router.get("/stream")                          # routes.py:50 — no auth dep
async def stream_reasoning(task: str):
    ... gather(*[run_agent(agent) for agent in reasoning_engine.agents])   # 3 agents
```

- **Runtime (TestClient, no credentials): `200 text/event-stream`**, body begins `data: [START] Thinking...` then `data: [AGENT] heuristic: [OLLAMA ERROR] ...` — the full probe sequence completed: 3 agents (`heuristic`, `optimizer`, `explorer`, introspected at import) each called `call_llm` → `httpx.AsyncClient(timeout=60.0)` POST to **hardcoded** `http://localhost:11434/api/generate`, model **`llama3`** hardcoded in `llm.py:8-11` (settings say `llama3.2` — drift), and on failure **interpolates `str(e)` into the streamed text** (`llm.py:20`).
- With Ollama up (normal deployment), each anonymous request = 3× up-to-60 s upstream LLM generations. With it down (this probe): instant refusal, still 3 doomed HTTP calls. Either way: **unauthenticated resource consumption + an unauthenticated proxy path to a host-local inference server + error-string disclosure.**
- Guarding it is one line today (`PROTECTED_CONTROL_PREFIXES` or a route dep) — but the real defect is structural: see §12 (allow-by-default). No tracked test asserts `/stream` requires auth.
- Rate limiting: `/stream` falls in the **general** bucket (100/min, shared with `/`, `/health`, all `/observation/*`) — the cheapest possible DoS amplifier: anonymous 100 windows/hour × 3 LLM calls each.

---

## 4. Error-shape contract — two 401s and a 500-pretending-to-be-429 (EV-A04-002/003/006)

**Side-by-side, same process, same key material:**

| Trigger | Status | Shape | Headers |
|---|---|---|---|
| `GET /evolve/runs` unauth (middleware) | 401 | **flat** `{"code","message"}` — no `error.category/severity/traceId`, no `recovery`, no `provenance` (`security.py:38-44`) | full `SecurityHeadersMiddleware` set + `X-RateLimit-*` |
| `GET /observation/capabilities` unauth (route dep) | 401 | **full ErrorEnvelope** (`metadata`/`error`/`recovery` + traceId) via `UnauthenticatedError` → `_domain` handler | same |
| 21st `/evolve` request (rate limiter) | **500** | envelope, but `code=PLATFORM_INTERNAL`, `message="Internal platform error"` | **none of them** — no `X-Content-Type-Options`, no CSP/HSTS, no `Retry-After`, no `X-RateLimit-*`; `server: uvicorn` **present** |

Mechanism of row 3 (`CONFIRMED` over uvicorn, phase-2b): `RateLimitMiddleware` (a `BaseHTTPMiddleware` sitting *outside* `SecurityHeadersMiddleware` and *outside* `ExceptionMiddleware`) does `raise HTTPException(429, …headers={"Retry-After": …})` (`rate_limit.py:122-137`). The exception never reaches the `StarletteHTTPException` handler (which is installed on the inner `ExceptionMiddleware`); it unwinds to `ServerErrorMiddleware`, which dispatches our catch-all `Exception` handler (`error_handler.py:161-180`) → **status 500, generic envelope, every HTTPException header dropped, `_secure()` never runs**. The limiter's carefully-built `Retry-After`/`X-RateLimit-*`/429 status are all discarded between `rate_limit.py:122` and the client.

So the platform's actual abuse signal is "internal error, retry in 5 s" (the catch-all's recovery hint) instead of "429, retry in 59 s". Clients cannot back off correctly; monitoring that counts 429s sees nothing; and this exact response is missing the entire hardening header set that every 200/401 carries (§6).

Tracked documents that promise the broken behavior: `Production Fitness Scoring.md:365` ("21st+ request should return 429 Too Many Requests") and `autonomous-api/PRODUCTION_HARDENING.md:250` (same) — both verified tracked at `6e1aa1a`.

---

## 5. Rate limiting as a control (EV-A04-003 cont., EV-A04-007)

**What the limiter actually is** (`rate_limit.py`): two module-level `RateLimiter` instances, hardcoded `evolution=20/60 s`, `general=100/60 s` (`:98-99`), sliding window of timestamps keyed by `request.client.host` (`:107`).

**Runtime burn sequence (uvicorn, phase-2b) — the important one:**

```
1× authed GET /evolve/runs          → 200, remaining=19
19× unauth GET /evolve/runs         → 401 each, remaining 18,17,…,1,0     # 401s COUNT
20th request (unauth)               → 500 PLATFORM_INTERNAL, no Retry-After, no security headers
21st request (VALID X-API-Key)      → 500 PLATFORM_INTERNAL               # operator locked out
GET /health meanwhile               → 200, remaining=98 (separate bucket)
```

- **Anonymous callers can lock the authenticated operator out of the entire `/evolve*` + `/production/readiness` control plane** for the rest of each rolling 60 s window, indefinitely, with 20 cheap requests — and because the limiter counts *before* `SecurityHeadersMiddleware` authenticates, 401-denied traffic is indistinguishable from real traffic to the budget. The operator's request then fails as a **500**, not a 429 telling them to wait.
- **Keying / proxy topology (`INFERRED` for deployment):** `request.client.host` with uvicorn **not** started `--proxy-headers` (Dockerfile `CMD` has no proxy flags, `Dockerfile:23`) means that behind nginx/Traefik/cloud-LB every external client shares **one** source IP → one global 20/min bucket for `/evolve*` for the whole internet, and the DoS in the previous bullet needs no target selection. (Direct-exposure deployments are per-IP as designed.)
- **Memory:** `cleanup_old_entries()` exists but has **zero callers** (`git grep` → only its definition, `rate_limit.py:150`). Per-key timestamp pruning happens on access (`:42-45`), but **keys for departed IPs are never deleted** → `self.requests` grows one entry per distinct source IP forever (slow leak; amplified under spoofed-varied-IP traffic if ever exposed directly).
- **Config lie (`IMPLEMENTED_SIMULATED`):** `RATE_LIMIT_GENERAL` / `RATE_LIMIT_EVOLUTION` / `RATE_LIMIT_WINDOW` are declared, env-mapped, validated positive (`config.py:28-30,50-54`), documented in `DEPLOYMENT_GUIDE.md:71-73` — and **never read by the limiter** (hardcoded at `rate_limit.py:98-99`). An operator who tunes the documented knobs changes nothing. Same class: `SECRET_KEY` (required in production, **never used anywhere** outside its own validator), `API_KEY_HEADER` (never passed to `ApiKeyAuthProvider` — `main.py:32` constructs with default `X-API-Key`), `LOG_FILE` (logger hardcodes `logs/app_{time:…}.log`, `logger.py:26`), `DATABASE_URL` (settings say `sqlite:///./evolution.db`; `db.py:9` hardcodes `sqlite:///data/evolution.db`). Five documented settings, zero effect.
- **Test gap:** `test_production_features.py:100-115` exercises the `RateLimiter` **class** only (allow/block/different-IPs). Nothing in any suite sends request 21 through the middleware — which is why the 429→500 break ships green.

---

## 6. Transport & configuration hardening (EV-A04-005/010/011 + health)

- **Headers (on 200/401/SSE):** `nosniff`, `X-Frame-Options DENY`, HSTS `includeSubDomains`, `Referrer-Policy`, `Permissions-Policy`, `Cache-Control no-store`, `server` deleted — all present on root/health/docs/401(flat)/401(envelope)/SSE probes (`CONFIRMED`). **Absent** on the rate-limit 500 (§4) and on CORS preflight responses (CORS short-circuits before `SecurityHeaders`; preflight probe showed only `ACAO`/`ACAC`/`Content-Type`).
- **CSP is weak while present:** `script-src 'self' 'unsafe-inline' 'unsafe-eval'` (`security.py:62-70`) — inline+eval kills XSS mitigation precisely on the `/docs`/`/redoc` pages that are public. `frame-ancestors 'none'` good.
- **CORS config-time validation is theater (`PARTIAL`, `CONFIRMED`):** `validate_cors_origins` accepts — adversarial inputs probed live: `http://localhost.evil.com` ✓, `https://localhost.evil.com` ✓, `https://totally-evil.example` ✓ (any https), `http://127.0.0.1.evil.com` ✓, `http://evil.com/localhost` ✓ (substring!). `"localhost" in origin` (`security.py:83`) is a substring test, not a host check. The **runtime** allowlist is still only whatever the operator configured (default `["http://localhost:3000"]` — request-time preflight from evil origins correctly gets no `ACAO`), so this is a broken safety-net, not a live CORS hole: an operator who relies on "validation will reject bad origins" is unprotected.
- **Preflight:** allowed-origin preflight on `/evolve/start` → 200 with `ACAO`+`ACAC:true` — bypasses auth **and** rate limiting by design (CORS outermost; correct CORS behavior, but it also means preflights are un-metered).
- **OPTIONS exemption:** non-preflight `OPTIONS /evolve/runs` → **405** (auth skipped via `method != "OPTIONS"`, `security.py:31`) — no data, but confirms the exemption is live; 405-vs-404 also confirms route existence without auth (moot while `/openapi.json` is public, §10).
- **Cookie channel without CSRF (`PARTIAL`, low):** `allow_credentials=True` + `cookie_name="api_key"` accepted (`security.py:112,129`). The app **never** sets this cookie (no `set_cookie` anywhere) — it only *accepts* one if something else planted it. Browsers' default `SameSite=Lax` blocks cross-site POSTs of such cookies; no CSRF token exists; risk materializes only for non-Lax/None cookies. Documented channel, missing defense-in-depth.
- **`/health` info disclosure (low):** anonymous 200 returns disk percent (`"critical: 96.6% used"` in probe), RSS/VMS MB, database status (`routes.py:26-48`). Useful to an attacker planning resource exhaustion; conventional for healthchecks but unauthenticated and detailed.

---

## 7. WebSocket rejection contract — claimed vs delivered (EV-A04-004)

| | Claimed (`ws.py:4-6,91-92` constitutional comment + code) | TestClient | **Real uvicorn (raw socket)** |
|---|---|---|---|
| Unauth upgrade | close **4401** + ErrorEnvelope as `reason` | `WebSocketDisconnect(code=4401, reason=<full envelope JSON>)` — claim **delivered** | **`HTTP/1.1 403 Forbidden`, `Content-Length: 0`, empty body** — no code, no envelope, nothing |
| Authed upgrade | accept | session opens | `101 Switching Protocols` + correct `Sec-WebSocket-Accept` |

Mechanism: per ASGI, a `websocket.close` sent *before* `accept` cannot become a WebSocket close frame — the handshake has not completed — so the server answers the HTTP upgrade with 403. The envelope built by `_auth_rejection_envelope()` (`ws.py:72-81`) **is computed and passed to `close()` but never reaches a real client**. Enforcement is `IMPLEMENTED_REAL` (fail-closed: nobody upgrades unauthenticated — 403 ×2, 101 with key ×2); the **rejection contract** is `IMPLEMENTED_SIMULATED` (true only under the in-process test harness). The only tracked test (`test_ws_never_accepts_anonymous`) asserts a generic `Exception`, so both semantics pass it.

Also note: any authenticated WS client can `{"type":"subscribe","run_id":…}` to **any** run (`ws.py:111-114`) — harmless under the single-key model (§8), but it is an unscoped broadcast join if keys are ever split per tenant.

---

## 8. Authorization model (EV-A04-009/012)

- **`AuthContext.scopes` is decorative:** `ApiKeyAuthProvider` returns `scopes=("observe","control")`, `subject="admin"` hardcoded (`security.py:131,143`); `git grep '\.scopes'` across `autonomous-api/` → **zero reads**. No route distinguishes observe vs control; there is no second principal. The data model advertises RBAC granularity that does not exist (`IMPLEMENTED_SIMULATED`). Single flat admin key = full control of `/evolve*` (including destructive `clear-memory`) and `/observation/*` alike.
- **`/evolve/sync` unbounded (`PARTIAL`):** `generations: int = 5, population_size: int = 8` as **raw query params with no `ge`/`le`** (`routes.py:96`) vs `EvolutionRequest.generations le=100/population_size le=100` on the body path — an authenticated caller can invoke `run_synchronous(..., use_docker=False)` with arbitrary magnitudes (no runtime probe performed — side effects; static only, `CONFIRMED` by code). The prefix auth does hold; this is resource-bound asymmetry, not authz bypass.
- **Prefix design (structural):** `PROTECTED_CONTROL_PREFIXES` is a deny-list of two prefixes; everything else added to the router is public unless its author remembers a `Depends`. `/stream` is the live proof that they sometimes don't (§3, §12).

---

## 9. Generated-artifact auth boundary (cross-ref EV-A03-007, not re-argued)

Carried forward with only boundary-relevant detail: Python lowering is fail-closed on missing env (401), codegen raises `ValueError` for auth ∉ `{jwt,api_key,basic}` (`builder.py:396-398` — an empty/unknown `genome.auth` can never ship an unauthed router: the security file generation fails first, `compile_and_materialize` raises before `materialize` writes), `AUTH_MODE` env override to an unsupported value → generated app 500s (`fail-closed`, `builder.py:427`), and the generated JWT verify pins HS256 but **does not `require: ["exp"]`** (no expiry enforcement in the emitted decode). **Go lowering remains fail-open** (default secrets) — EV-A03-007, pending collaborator remediation track. One adjacent static note: `self_healing.py:162` can inject `auth: "oauth2"` into a genome; codegen then raises `ValueError` (fail-closed — capability loss, not a security hole).

---

## 10. Published security contract (EV-A04-008/013/014/016)

- **OpenAPI declares zero security:** live `/openapi.json` → `components.securitySchemes = {}`, **0 of 17 operations** carry a `security` key, no top-level `security`. `Depends(require_auth)` without `Security(...)` leaves the published contract silent — a consumer (or codegen tool) reading the spec sees an entirely open API. `IMPLEMENTED_SIMULATED` at the contract layer: enforcement exists, advertisement doesn't.
- **`/docs`+`/redoc` public is intentional** (`test_docs_endpoint_accessible` asserts 200) — combined with the silent spec, the public docs present the platform as anonymous.
- **Tracked 429 claims are false** (§4): `Production Fitness Scoring.md:365`, `PRODUCTION_HARDENING.md:250`.
- **`DEPLOYMENT_GUIDE.md:215` ships an example auth middleware using `api_key != expected_key`** (non-constant-time) — docs-only; every shipped comparison uses `compare_digest`. Doc/example drift, not runtime.

---

## 11. Test & CI coverage of the boundary (EV-A04-015)

| Claim | What actually runs |
|---|---|
| App auth fail-closed | `autonomous-api/tests/observation/test_auth_fail_closed.py` — **7/7 passed** here; covers unconfigured→401, envelope shape on `/observation/*`, header/bearer channels |
| Control-plane prefix + headers + docs | `test_production_features.py` (`/evolve/start` 401, `/evolve/elite/start` 401, `/docs` 200, header set) |
| Rate limiting | `RateLimiter` **class only** (`test_production_features.py:100-115`) — the 429→500 middleware break is **untested** |
| `/stream` requires auth | **no test** |
| WS rejection contract | asserts generic `Exception` only — 4401/envelope/403 never pinned |
| Which suite does CI run? | `ci-cd.yml:14,50`: `working-directory: autonomous-api` → **`pytest tests/` = `autonomous-api/tests` only**; root `tests/` (~4300 tests, incl. `tests/test_r33_*` security tests for the *tiannara* layer, not `app/`) runs only in subset gates, never wholesale |
| Can a clean env run the canonical suite at all? | **No:** `pyproject` dev extras = `pytest` only; `hypothesis` is imported by `tests/test_governance_genes.py` + `tests/test_phase28_voting.py` but **undeclared** → `pip install -e .[dev] && python -m pytest` → 2 collection errors → **"Interrupted: 2 errors during collection" aborts the entire run**, security tests included. Reproduced in this audit with the project venv (system Python happens to have hypothesis globally → 4254/4303 collected, 0 errors). |

Net: the security boundary has ~7 real tests, all in one file, none covering `/stream`, the middleware 429 path, WS rejection details, or CORS validation — and CI never runs the root suite where the broader `r33` security tests live.

---

## 12. Invariant search (absences recorded as findings)

| Invariant | Present? | Evidence of (absence) |
|---|---|---|
| every non-public route is authed (allow-list for anonymous) | **NO** | deny-by-prefix design; `/stream` anonymous (§3) |
| anonymous traffic cannot exhaust a control-plane budget | **NO** | 19×401 → operator 500 lockout (§5) |
| rate-limited response = 429 + `Retry-After` | **NO** | 500 `PLATFORM_INTERNAL`, headers dropped (§4) |
| every error response carries the hardening header set | **NO** | rate-limit 500 has none; `server` header returns (§4) |
| one 401 shape platform-wide | **NO** | flat (middleware) vs envelope (route dep) (§4) |
| documented setting ⇒ runtime effect | **NO** | 5 dead settings (§5) |
| WS rejection delivers code+reason to the peer | **NO** (real transport) | 403 empty body (§7) |
| published OpenAPI reflects auth requirements | **NO** | 0/17 ops, no schemes (§10) |
| `scopes` claim ⇒ enforcement | **NO** | zero `.scopes` reads (§8) |
| config validator ⇒ safe origin list | **NO** (substring/any-https) | §6 |
| path confusion ⇒ still protected | **YES** | `/evolvex` 401, `/%65volve` 401, case/double-slash → 404 not 200 (§1) |
| query string never authenticates | **YES** | `?api_key=` → 401 (§2) |
| unconfigured/production ⇒ fail-closed | **YES** | double gate + 7-test suite (§2) |
| auth before accept on WS | **YES** (enforcement) | 403/101 raw (§7) |

---

## 13. Blocker register — EV-A04-001 … EV-A04-017

| ID | Finding | Taxonomy | Conf | Evidence | Boundary | Implication | Indep.? |
|---|---|---|---|---|---|---|---|
| **EV-A04-001** | `GET /stream` fully anonymous: 3 agents × 60 s-timeout LLM calls fan out per request; streams `str(e)` from the LLM client; hardcoded `llama3` URL drift from settings; no test | anonymous control path `UNIMPLEMENTED` | CONFIRMED | `routes.py:50-64`; `llm.py:4-20`; probe `anon_stream` 200 SSE; `orchestrator` agents=3 | resource boundary; host-local inference exposure; info leak | unauth DoS amplifier + unauth LLM proxy + error disclosure | **Independent** |
| **EV-A04-002** | Two divergent 401 shapes: flat `{code,message}` (middleware, no recovery/provenance) vs full ErrorEnvelope (route dep) | error contract `PARTIAL` | CONFIRMED | `security.py:38-44` vs `error_handler.py:88-124`; probe side-by-side | error-contract truthfulness | clients must handle two schemas; recovery guidance absent on control-plane 401 | **Independent** |
| **EV-A04-003** | Rate-limited requests return **500 `PLATFORM_INTERNAL`**, not 429: `HTTPException` raised outside `ExceptionMiddleware` → catch-all handler; `Retry-After`/`X-RateLimit-*`/status all dropped; tracked docs (`Production Fitness Scoring.md:365`, `PRODUCTION_HARDENING.md:250`) promise 429 | rate-limit response contract `PARTIAL` (throttles, wrong contract) | CONFIRMED | `rate_limit.py:122-137`; `error_handler.py:161-180`; uvicorn phase-2b records; docs lines | abuse-control contract; monitoring; doc truthfulness | clients can't back off; 429-metrics blind; "internal error" noise | **Independent** |
| **EV-A04-004** | Unauth 401s counted before auth exhaust the shared per-IP `/evolve` bucket → **valid-key operator receives 500 for the rest of each 60 s window** (anonymous repeatable control-plane lockout); behind a non-proxy-aware uvicorn all clients share one bucket (`INFERRED`); departed-IP keys never GC'd (`cleanup_old_entries` zero callers) | rate-limit keying/accounting `PARTIAL` | CONFIRMED (burn/lockout) / INFERRED (proxy topology) | `rate_limit.py:107,118-137,150`; `Dockerfile:23`; phase-2b seq: 401×19 → 500 → authed 500 | availability of authenticated control plane | 20 anonymous requests = 60 s operator outage, renewable forever | **Independent** |
| **EV-A04-005** | Error/short-circuit responses escape the hardening layer: rate-limit 500 has **no** security headers and `server: uvicorn` reappears; CORS preflight responses likewise skip `SecurityHeadersMiddleware` | header application `PARTIAL` | CONFIRMED | probe headers on 500/preflight vs 200/401; stack order `[Prometheus,CORS,RateLimit,SecurityHeaders]` | transport hardening consistency | weakest responses (errors) get the least hardening | Refinement of 003 |
| **EV-A04-006** | CSP ships `unsafe-inline` + `unsafe-eval` while `/docs`+`/redoc` are public | CSP `PARTIAL` | CONFIRMED | `security.py:62-70`; probe CSP header | XSS mitigation on docs pages | swagger UI posture; XSS blast radius | **Independent** |
| **EV-A04-007** | Five documented settings wired to nothing: `SECRET_KEY` (prod-required, never read), `API_KEY_HEADER`, `RATE_LIMIT_*`×3, `LOG_FILE`, `DATABASE_URL` | configuration `IMPLEMENTED_SIMULATED` | CONFIRMED | `config.py:24-33,62`; `main.py:32`; `rate_limit.py:98-99`; `logger.py:26`; `db.py:9`; `DEPLOYMENT_GUIDE.md:66-77` | operator security posture | tuning documented knobs silently no-ops (incl. rate limits + "secret") | **Independent** |
| **EV-A04-008** | OpenAPI: `securitySchemes={}`, **0/17** operations declare `security`; no top-level `security` — published contract shows a fully open API | published contract `UNIMPLEMENTED` | CONFIRMED | probe `openapi_security` record | consumer-facing auth contract | consumers/codegen trust a spec that hides all auth | **Independent** |
| **EV-A04-009** | `AuthContext.scopes=("observe","control")` never read anywhere; `subject="admin"` hardcoded — decorative RBAC, single flat key owns control+observe alike | authorization model `IMPLEMENTED_SIMULATED` | CONFIRMED | `security.py:91-94,131`; `git grep '\.scopes'` → 0 hits | authorization truthfulness | future multi-key plans inherit a field that never worked; no least-privilege split possible today | **Independent** |
| **EV-A04-010** | WS rejection contract false on real transport: claims close **4401 + ErrorEnvelope reason**; uvicorn delivers **403 empty body** (envelope computed, discarded). Enforcement itself is sound (403/101) | rejection contract `IMPLEMENTED_SIMULATED` / enforcement `IMPLEMENTED_REAL` | CONFIRMED | `ws.py:4-6,72-94`; raw-socket probes (403/`Content-Length: 0`, 101); TestClient `WebSocketDisconnect(4401, envelope)`; test asserts only `Exception` | WS auth boundary contract | operators/clients debugging 403s get zero reason; constitutional comment overclaims | **Independent** |
| **EV-A04-011** | Config-time CORS validation: substring `"localhost" in origin` accepts `http://localhost.evil.com` / `http://evil.com/localhost` / `http://127.0.0.1.evil.com`; **any** `https://` accepted; only runtime default (`localhost:3000`) keeps this from being a live hole | origin validation `PARTIAL` | CONFIRMED | `security.py:74-87`; probe `cors_validate_adversarial` (5/7 adversarial accepted) | CORS safety net | operator who trusts "validation" can permanently allow attacker origins | **Independent** |
| **EV-A04-012** | Cookie auth channel live (`api_key` cookie accepted) + `allow_credentials=True`, **no CSRF token, no SameSite control** (app never sets the cookie; browser Lax default is the only shield) | CSRF defense `PARTIAL` (low) | CONFIRMED | `security.py:112,129`; `main.py:55`; probe `auth_cookie` 200; no `set_cookie` in tree | credentialed cross-site requests | CSRF if a non-Lax cookie is ever planted for the origin | **Independent** |
| **EV-A04-013** | `/evolve/sync` accepts unbounded raw-query `generations`/`population_size` (no `ge/le`) vs `EvolutionRequest(le=100)` on the body path → authenticated resource exhaustion asymmetry | input bounds `PARTIAL` | CONFIRMED (static; not invoked) | `routes.py:96-98`; `schemas/evolution.py` le=100 | control-plane resource bounds | authed DoS via thread-pool sync evolution | **Independent** |
| **EV-A04-014** | Anonymous `/health` discloses disk %, RSS/VMS MB, database status | health disclosure `IMPLEMENTED_REAL` (over-broad) | CONFIRMED | `routes.py:26-48`; probe `anon_health` | infra reconnaissance | sizes a resource-exhaustion attack; conventional-endpoint tension | **Independent** |
| **EV-A04-015** | Boundary test/CI gap: `hypothesis` undeclared (dev extras = pytest only) → clean-env canonical `python -m pytest` **aborts at collection** (2 errors) incl. security tests; `ci-cd.yml` runs only `autonomous-api/tests`; root `tests/` security files (`test_r33_*`) never in CI; no tests for `/stream` auth, middleware-429 shape, WS rejection detail, CORS validation | evidence pipeline `PARTIAL`→`UNIMPLEMENTED` (coverage) | CONFIRMED | `pyproject.toml:14-16`; venv reproduction (2 errors); system Python 4254/4303 0 err; `ci-cd.yml:14,50`; test greps | security regression gate | the boundary can regress silently; clean envs can't run the gate at all | **Independent** |
| **EV-A04-016** | Generated-artifact auth (boundary carry-over): JWT decode without `require:["exp"]`; `AUTH_MODE` env can force unsupported mode → 500 (fail-closed); `oauth2` injection → codegen `ValueError` (fail-closed); **Go fail-open defaults remain live pending collaborator track** | artifact auth `PARTIAL` (Python bounded, Go fail-open) | CONFIRMED | `builder.py:396-427`; `self_healing.py:162`; EV-A03-007 | generated-service auth boundary | exp-less JWTs are forever tokens; Go artifacts ship default credentials | Cross-ref EV-A03-007 |
| **EV-A04-017** | Structural: protection is a two-prefix deny-list (`PROTECTED_CONTROL_PREFIXES`); everything else is public unless the route author adds a dep — no invariant, no lint, no test enforcing "mutating/intensive routes are authed" (the `/stream` precedent) | boundary design `PARTIAL` | CONFIRMED (design + instance) | `security.py:21-24`; `/stream` §3; invariant table §12 | long-term boundary integrity | every future route is one forgotten `Depends` from anonymous | **Independent** (root cause of 001) |

---

## 14. EV-A04 CONCLUSION (direct answer)

**Does the platform enforce the security boundary it advertises?**

- **Authentication core: yes.** Fail-closed everywhere it matters (unconfigured, production startup, bad keys, query-string tricks, WS upgrade), constant-time compares, prefix protection that survives path confusion, auth-before-validation and auth-before-accept. This is real, tested (7 tests), and reproduced at runtime over both harnesses.
- **Boundary coverage: no.** The anonymous surface is an allow-by-default complement of a two-prefix deny-list, and it already leaked: `/stream` executes multi-second LLM work for anyone who can reach it. OpenAPI publishes zero security declarations, `scopes` are decorative, five documented security settings do nothing, and the CORS validator rubber-stamps attacker origins.
- **Abuse controls: no.** The rate limiter throttles but ships the **wrong protocol** (500 instead of 429, headers dropped, hardening headers absent), counts anonymous 401s against the operator's budget (demonstrated lockout), ignores its own documented configuration, doesn't understand reverse proxies, and never garbage-collects its keys — while the docs promise 429s it cannot emit.
- **WS contract: enforcement yes, delivery no** — real clients get an empty 403, not the promised 4401 envelope.

**STATUS: FAIL** stands on the three demonstrated contract breaches (anonymous `/stream` resource path, 429→500 + operator lockout, WS 4401-overclaim) plus the published-contract silence (0/17 security declarations). The fail-closed key-auth core is the part that is genuinely done; everything around it — coverage, accounting, advertisement, configuration — is not.

**Positive controls (do not regress):** production double gate; unconfigured→401 (7 tests); `compare_digest` everywhere; no URL tokens; decode-then-check prefix matching; path-confusion immunity; auth-before-validation; auth-before-accept enforcement; validation errors leak field names only; hardening headers on all normal-path responses; non-root Docker user; generated-Python fail-closed auth env handling.

Carried forward: EV-A04-001…017; interacts with EV-A01-001 (Bandit red, separate track), EV-A03-007 (Go fail-open), EV-A02-007 (backend divergence), PROD-A01 (deployment inventory — proxy topology feeds EV-A04-004's `INFERRED` half).

## 15. NEXT GATE

**EV-A05 — Deployment.** The boundary's remaining unknowns are deployment-shaped: does the shipped compose/systemd/guide path actually set `ADMIN_API_KEY`+`SECRET_KEY` (the two that validate), terminate TLS, put a proxy in front (→ EV-A04-004's shared-bucket `INFERRED` becomes `CONFIRMED` or dead), pin `--proxy-headers`, and run non-root as the Dockerfile does? EV-A04-007's dead settings also need the deployment docs' view: what PROD-A01 recorded the deploy story to actually promise vs. what `config.py` honors.

## 16. Verification appendix (reproducible)

```text
runtime probes (cwd=temp, repo untouched):
  .../Temp/opencode/ev04/ev04_probe.py       # TestClient, 32 records
  .../Temp/opencode/ev04/ev04_uvicorn2.py     # uvicorn :18766 — burn/limited/lockout
  .../Temp/opencode/ev04/ev04_uvicorn3.py     # uvicorn :18767 — WS isolation matrix
  .../Temp/opencode/ev04/ev04_uvicorn4.py     # uvicorn :18768 — exact-sequence confirm
static:
  git grep -n "\.scopes" autonomous-api/                    # 0 hits
  git grep -n "cleanup_old_entries"                         # definition only
  git grep -n "SECRET_KEY\|API_KEY_HEADER\|RATE_LIMIT_" autonomous-api/app
  git show 6e1aa1a:autonomous-api/app/middleware/security.py   # prefixes :24, 401 :38-44, cors :74-87
  git show 6e1aa1a:autonomous-api/app/middleware/rate_limit.py # raise :122-137, hardcode :98-99
suite evidence:
  system python -m pytest --collect-only    # 4254/4303, 0 errors (hypothesis present globally)
  venv python -m pytest --collect-only      # 2 collection errors (hypothesis missing) = clean-env break
  autonomous-api/.venv python tests/observation/test_auth_fail_closed.py   # 7 passed
harness note:
  ev04_uvicorn.py runs 1-2 timed out on the first unauth request after raw WS
  probes; identical sequence with uvicorn stdout redirected to a FILE
  (ev04_uvicorn4.py) completed cleanly → undrained subprocess PIPE artifact of
  the probe, NOT platform behavior; not registered as a finding.
```

*Internal analysis doc — working tree only, not tracked (per AGENTS.md .md policy).*
