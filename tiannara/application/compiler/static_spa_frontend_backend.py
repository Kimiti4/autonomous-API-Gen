"""StaticSpaFrontendBackend -- a user-facing surface derived from the ISR.

Consumes the typed SystemModel and deterministically emits a self-contained
single-page application:

  * ``app.js``      -- ESM module: resource descriptors, URL/header helpers, a
                       pure reducer, payload coercion, and injectable-fetch API
                       helpers (create/list/get/replace/delete), plus a DOM boot
                       sequence guarded so the module is importable in Node.
  * ``tests/app.test.mjs`` -- executable ``node --test`` suite over the pure
                       exports (no network, no DOM).
  * ``smoke.mjs``   -- non-browser runtime smoke driver that exercises a live
                       server over HTTP (health, auth, CRUD round-trip).
  * static assets   -- ``index.html`` / ``styles.css`` / ``serve.py`` /
                       ``Dockerfile`` for local serving and container builds.

Design constraints (mirrors the FastAPI/Go backends):
  * structure derives solely from the ISR (resources == data models, field
    controls == abstract field types); nothing is hard-coded per product;
  * the bundle roots at ``<slug>/frontend/`` so multi-backend fleets sharing
    one project root never collide;
  * generated tests pass on first run against the generated code itself.
"""

from __future__ import annotations

import json

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
    SystemModel,
)

from .naming import pluralize, slugify, snake_case

_CONTROL_BY_TYPE: dict[AbstractFieldType, str] = {
    AbstractFieldType.IDENTIFIER: "text",
    AbstractFieldType.TEXT: "text",
    AbstractFieldType.INTEGER: "number",
    AbstractFieldType.DECIMAL: "number",
    AbstractFieldType.BOOLEAN: "checkbox",
    AbstractFieldType.TIMESTAMP: "datetime-local",
    AbstractFieldType.ENUMERATION: "select",
    AbstractFieldType.REFERENCE: "text",
    AbstractFieldType.BINARY: "text",
    AbstractFieldType.DOCUMENT: "text",
}

_APP_JS_TEMPLATE = """\
export const RESOURCES = <<RESOURCES>>;
export const PRIMARY = "<<PRIMARY>>";

export function apiUrl(base, path, id) {
  const root = String(base || "").replace(/\\/+$/, "");
  const suffix = String(path || "").replace(/^\\/+/, "");
  const tail =
    id === undefined || id === null || id === ""
      ? ""
      : "/" + encodeURIComponent(String(id));
  return `${root}/${suffix}${tail}`;
}

export function headers(apiKey) {
  const result = { "Content-Type": "application/json" };
  if (apiKey) {
    result["X-API-Key"] = String(apiKey);
  }
  return result;
}

export function initialState() {
  return { items: [], loading: false, error: null };
}

export function reducer(state, action) {
  switch (action.type) {
    case "loading":
      return { ...state, loading: true, error: null };
    case "loaded":
      return {
        ...state,
        loading: false,
        items: Array.isArray(action.items) ? action.items : [],
        error: null,
      };
    case "error":
      return { ...state, loading: false, error: String(action.error || "request failed") };
    case "created": {
      const item = action.item;
      const rest = state.items.filter((entry) => entry.id !== item.id);
      return { ...state, loading: false, items: [item, ...rest], error: null };
    }
    case "updated": {
      const item = action.item;
      return {
        ...state,
        loading: false,
        items: state.items.map((entry) => (entry.id === item.id ? item : entry)),
        error: null,
      };
    }
    case "deleted":
      return {
        ...state,
        loading: false,
        items: state.items.filter((entry) => entry.id !== action.id),
        error: null,
      };
    default:
      return state;
  }
}

export function toPayload(form, fields) {
  const payload = {};
  for (const field of fields) {
    if (field.name === "id") continue;
    const raw = form ? form[field.name] : undefined;
    const missing = raw === undefined || raw === null || raw === "";
    if (missing) {
      if (field.required) {
        if (field.control === "number") payload[field.name] = 0;
        else if (field.control === "checkbox") payload[field.name] = false;
        else payload[field.name] = "";
      }
      continue;
    }
    if (field.control === "number") payload[field.name] = Number(raw);
    else if (field.control === "checkbox") payload[field.name] = Boolean(raw);
    else payload[field.name] = raw;
  }
  return payload;
}

export function advanceStatus(resource, item) {
  const field = resource.fields.find((entry) => entry.name === "status");
  if (!field || !field.options || field.options.length === 0) return null;
  const current = field.options.indexOf(item.status);
  const next = field.options[(current + 1) % field.options.length];
  return toPayload({ ...item, status: next }, resource.fields);
}

export async function fetchList(fetchImpl, base, apiKey, path) {
  const response = await fetchImpl(apiUrl(base, path), {
    method: "GET",
    headers: headers(apiKey),
  });
  if (!response.ok) {
    throw new Error(`list ${path} failed with status ${response.status}`);
  }
  return response.json();
}

export async function createItem(fetchImpl, base, apiKey, path, payload) {
  const response = await fetchImpl(apiUrl(base, path), {
    method: "POST",
    headers: headers(apiKey),
    body: JSON.stringify(payload),
  });
  if (!response.ok && response.status !== 201) {
    throw new Error(`create ${path} failed with status ${response.status}`);
  }
  return response.json();
}

export async function updateItem(fetchImpl, base, apiKey, path, id, payload) {
  const response = await fetchImpl(apiUrl(base, path, id), {
    method: "PUT",
    headers: headers(apiKey),
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`replace ${path} failed with status ${response.status}`);
  }
  return response.json();
}

export async function deleteItem(fetchImpl, base, apiKey, path, id) {
  const response = await fetchImpl(apiUrl(base, path, id), {
    method: "DELETE",
    headers: headers(apiKey),
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(`delete ${path} failed with status ${response.status}`);
  }
  return true;
}

function fieldControl(field) {
  const wrap = document.createElement("label");
  wrap.textContent = field.label;
  let control;
  if (field.control === "select") {
    control = document.createElement("select");
    for (const option of field.options) {
      const element = document.createElement("option");
      element.value = option;
      element.textContent = option;
      control.appendChild(element);
    }
  } else if (field.control === "checkbox") {
    control = document.createElement("input");
    control.type = "checkbox";
  } else if (field.control === "number") {
    control = document.createElement("input");
    control.type = "number";
  } else if (field.control === "datetime-local") {
    control = document.createElement("input");
    control.type = "datetime-local";
  } else {
    control = document.createElement("input");
    control.type = "text";
  }
  control.name = field.name;
  wrap.appendChild(control);
  return wrap;
}

async function boot() {
  const formEl = document.getElementById("resource-form");
  const listEl = document.getElementById("resource-list");
  const errorEl = document.getElementById("error-banner");
  const baseEl = document.getElementById("api-base");
  const keyEl = document.getElementById("api-key");
  if (!formEl || !listEl) return;
  const resource =
    RESOURCES.find((entry) => entry.path === PRIMARY) || RESOURCES[0];
  if (!resource) {
    if (errorEl) errorEl.textContent = "no resources declared";
    return;
  }
  for (const field of resource.fields) formEl.appendChild(fieldControl(field));
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.textContent = "Create";
  formEl.appendChild(submit);

  const fetchImpl =
    typeof fetch === "function"
      ? fetch.bind(typeof window === "undefined" ? globalThis : window)
      : null;
  const base = () => (baseEl && baseEl.value.trim()) || "http://127.0.0.1:8000";
  const key = () => (keyEl ? keyEl.value.trim() : "");
  const refreshEl = document.getElementById("refresh");
  let state = initialState();

  function paint() {
    if (errorEl) errorEl.textContent = state.error || "";
    listEl.textContent = "";
    for (const item of state.items) listEl.appendChild(rowFor(item));
  }

  function rowFor(item) {
    const row = document.createElement("li");
    row.setAttribute("data-id", item.id);
    const summary = document.createElement("span");
    summary.textContent = resource.fields
      .map((field) => String(item[field.name] ?? ""))
      .filter(Boolean)
      .join(" - ");
    row.appendChild(summary);
    if (resource.fields.some((field) => field.name === "status")) {
      const advanceButton = document.createElement("button");
      advanceButton.type = "button";
      advanceButton.textContent = "Advance";
      advanceButton.addEventListener("click", () => {
        void advance(item);
      });
      row.appendChild(advanceButton);
    }
    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", () => {
      void removeItem(item);
    });
    row.appendChild(deleteButton);
    return row;
  }

  async function refresh() {
    state = reducer(state, { type: "loading" });
    try {
      const items = await fetchList(fetchImpl, base(), key(), resource.path);
      state = reducer(state, { type: "loaded", items });
    } catch (err) {
      state = reducer(state, { type: "error", error: err.message });
    }
    paint();
  }

  async function advance(item) {
    const payload = advanceStatus(resource, item);
    if (!payload) return;
    state = reducer(state, { type: "loading" });
    try {
      const updated = await updateItem(
        fetchImpl,
        base(),
        key(),
        resource.path,
        item.id,
        payload
      );
      state = reducer(state, { type: "updated", item: updated });
    } catch (err) {
      state = reducer(state, { type: "error", error: err.message });
    }
    paint();
  }

  async function removeItem(item) {
    state = reducer(state, { type: "loading" });
    try {
      await deleteItem(fetchImpl, base(), key(), resource.path, item.id);
      state = reducer(state, { type: "deleted", id: item.id });
    } catch (err) {
      state = reducer(state, { type: "error", error: err.message });
    }
    paint();
  }

  formEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = {};
    for (const field of resource.fields) {
      const control = formEl.elements[field.name];
      if (!control) continue;
      values[field.name] = field.control === "checkbox" ? control.checked : control.value;
    }
    state = reducer(state, { type: "loading" });
    try {
      const payload = toPayload(values, resource.fields);
      const created = await createItem(
        fetchImpl,
        base(),
        key(),
        resource.path,
        payload
      );
      state = reducer(state, { type: "created", item: created });
      formEl.reset();
    } catch (err) {
      state = reducer(state, { type: "error", error: err.message });
    }
    paint();
  });

  if (refreshEl) {
    refreshEl.addEventListener("click", () => {
      void refresh();
    });
  }

  paint();
  await refresh();
}

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      void boot();
    });
  } else {
    void boot();
  }
}
"""

_APP_TEST_TEMPLATE = """\
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  advanceStatus,
  apiUrl,
  createItem,
  deleteItem,
  fetchList,
  headers,
  initialState,
  reducer,
  toPayload,
  updateItem,
} from "../app.js";

const FIELDS = <<FIELDS>>;

test("apiUrl joins base, path and id without duplicate slashes", () => {
  assert.equal(apiUrl("http://localhost:8000/", "/tasks", "t-1"), "http://localhost:8000/tasks/t-1");
  assert.equal(apiUrl("http://localhost:8000", "tasks"), "http://localhost:8000/tasks");
  assert.equal(apiUrl("", "tasks", null), "/tasks");
});

test("apiUrl encodes identifiers safely", () => {
  assert.equal(apiUrl("http://h", "tasks", "a b/c"), "http://h/tasks/a%20b%2Fc");
});

test("headers carry the api key only when supplied", () => {
  assert.deepEqual(headers(""), { "Content-Type": "application/json" });
  assert.deepEqual(headers("secret"), {
    "Content-Type": "application/json",
    "X-API-Key": "secret",
  });
});

test("reducer loading clears the previous error", () => {
  const failed = reducer(initialState(), { type: "error", error: "boom" });
  const loading = reducer(failed, { type: "loading" });
  assert.equal(loading.loading, true);
  assert.equal(loading.error, null);
});

test("reducer loaded replaces items and success states", () => {
  const state = reducer(initialState(), {
    type: "loaded",
    items: [{ id: "1" }, { id: "2" }],
  });
  assert.deepEqual(state.items.map((item) => item.id), ["1", "2"]);
  assert.equal(state.loading, false);
  assert.equal(state.error, null);
});

test("reducer created deduplicates by id and prepends", () => {
  let state = reducer(initialState(), { type: "loaded", items: [{ id: "1" }] });
  state = reducer(state, { type: "created", item: { id: "2" } });
  state = reducer(state, { type: "created", item: { id: "2", title: "again" } });
  assert.equal(state.items.length, 2);
  assert.equal(state.items[0].id, "2");
  assert.equal(state.items[0].title, "again");
});

test("reducer updated maps by id and deleted filters", () => {
  let state = reducer(initialState(), {
    type: "loaded",
    items: [{ id: "1", title: "a" }, { id: "2", title: "b" }],
  });
  state = reducer(state, { type: "updated", item: { id: "1", title: "z" } });
  assert.equal(state.items[0].title, "z");
  state = reducer(state, { type: "deleted", id: "2" });
  assert.deepEqual(state.items.map((item) => item.id), ["1"]);
});

test("reducer ignores unknown actions", () => {
  const state = reducer(initialState(), { type: "nonsense" });
  assert.deepEqual(state, initialState());
});

test("toPayload drops empty optional fields and keeps required ones", () => {
  const form = {};
  for (const field of FIELDS) {
    if (field.control === "number") form[field.name] = "42";
    else if (field.control === "checkbox") form[field.name] = "on";
    else form[field.name] = `seed-${field.name}`;
    if (!field.required) form[field.name] = "";
  }
  const payload = toPayload(form, FIELDS);
  assert.equal("id" in payload, false);
  for (const field of FIELDS) {
    if (field.name === "id") continue;
    if (field.required) assert.ok(field.name in payload, `missing ${field.name}`);
    else assert.equal(field.name in payload, false, `kept ${field.name}`);
  }
});

test("toPayload coerces number and checkbox controls", () => {
  const fields = [
    { name: "id", control: "text", required: false, options: [] },
    { name: "count", control: "number", required: true, options: [] },
    { name: "done", control: "checkbox", required: false, options: [] },
  ];
  const payload = toPayload({ id: "x", count: "4", done: "on" }, fields);
  assert.equal(payload.count, 4);
  assert.equal(payload.done, true);
});

test("toPayload fills required controls that were never touched", () => {
  const fields = [
    { name: "title", control: "text", required: true, options: [] },
    { name: "notes", control: "text", required: false, options: [] },
  ];
  const payload = toPayload({}, fields);
  assert.equal(payload.title, "");
  assert.equal("notes" in payload, false);
});

test("advanceStatus cycles the status enum and never sends the id", () => {
  const resource = {
    path: "tasks",
    fields: [
      { name: "id", control: "text", required: false, options: [] },
      { name: "status", control: "select", required: true, options: ["open", "in_progress", "done"] },
      { name: "title", control: "text", required: true, options: [] },
    ],
  };
  const open = advanceStatus(resource, { id: "t1", status: "open", title: "Write code" });
  assert.equal(open.status, "in_progress");
  assert.equal("id" in open, false);
  const done = advanceStatus(resource, { id: "t1", status: "done", title: "Write code" });
  assert.equal(done.status, "open");
});

test("advanceStatus returns null when the resource has no status field", () => {
  const resource = { path: "lists", fields: [{ name: "name", control: "text", required: true, options: [] }] };
  assert.equal(advanceStatus(resource, { id: "l1", name: "Inbox" }), null);
});

function fakeFetch(responses) {
  const calls = [];
  const impl = async (url, init) => {
    calls.push({ url, init });
    const next = responses.shift();
    return {
      ok: next.ok,
      status: next.status,
      json: async () => next.body,
    };
  };
  return { impl, calls };
}

test("fetchList issues a GET with the api key header", async () => {
  const { impl, calls } = fakeFetch([{ ok: true, status: 200, body: [{ id: "1" }] }]);
  const items = await fetchList(impl, "http://api", "k", "tasks");
  assert.deepEqual(items, [{ id: "1" }]);
  assert.equal(calls[0].url, "http://api/tasks");
  assert.equal(calls[0].init.method, "GET");
  assert.equal(calls[0].init.headers["X-API-Key"], "k");
});

test("createItem posts JSON and accepts 201", async () => {
  const { impl, calls } = fakeFetch([{ ok: true, status: 201, body: { id: "new" } }]);
  const created = await createItem(impl, "http://api", "k", "tasks", { title: "x" });
  assert.equal(created.id, "new");
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.body, JSON.stringify({ title: "x" }));
});

test("createItem surfaces server rejections as errors", async () => {
  const { impl } = fakeFetch([{ ok: false, status: 422, body: {} }]);
  await assert.rejects(
    () => createItem(impl, "http://api", "k", "tasks", {}),
    /status 422/
  );
});

test("updateItem issues PUT to the item URL", async () => {
  const { impl, calls } = fakeFetch([{ ok: true, status: 200, body: { id: "t1", status: "done" } }]);
  const updated = await updateItem(impl, "http://api", "k", "tasks", "t1", { status: "done" });
  assert.equal(updated.status, "done");
  assert.equal(calls[0].url, "http://api/tasks/t1");
  assert.equal(calls[0].init.method, "PUT");
});

test("deleteItem tolerates 204 and reports success", async () => {
  const { impl, calls } = fakeFetch([{ ok: false, status: 204, body: undefined }]);
  assert.equal(await deleteItem(impl, "http://api", "k", "tasks", "t1"), true);
  assert.equal(calls[0].init.method, "DELETE");
});
"""

_SMOKE_JS_TEMPLATE = """\
#!/usr/bin/env node
// Non-browser runtime smoke: exercises a live server over HTTP.
// Usage: node smoke.mjs --base http://127.0.0.1:8000 --key KEY \\
//            --resource tasks --payload '{"title":"seed"}' \\
//            [--changes '{"status":"done"}']

const args = process.argv.slice(2);

function option(name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  return args[index + 1];
}

const base = option("--base", "http://127.0.0.1:8000").replace(/\\/+$/, "");
const apiKey = option("--key", "");
const resource = option("--resource", "<<PRIMARY>>");
const payload = JSON.parse(option("--payload", "{}"));
const changes = JSON.parse(option("--changes", "{}"));

const steps = [];

async function step(name, run) {
  try {
    const detail = await run();
    steps.push({ name, ok: true, detail });
  } catch (error) {
    steps.push({ name, ok: false, detail: String(error && error.message ? error.message : error) });
  }
}

function authHeaders(extra) {
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["X-API-Key"] = apiKey;
  return { ...headers, ...(extra || {}) };
}

async function expect(response, status, label) {
  if (response.status !== status) {
    let body = "";
    try {
      body = await response.text();
    } catch (error) {
      body = "";
    }
    throw new Error(`${label}: expected status ${status}, got ${response.status}: ${body.slice(0, 200)}`);
  }
  return response;
}

let createdId = null;

await step("health endpoint reports ok", async () => {
  const response = await fetch(`${base}/health`);
  await expect(response, 200, "health");
  const body = await response.json();
  if (body.status !== "ok") throw new Error(`health status was ${body.status}`);
  return "GET /health -> 200";
});

await step("resource list rejects requests without credentials", async () => {
  const response = await fetch(`${base}/${resource}`);
  await expect(response, 401, "unauthenticated list");
  return `GET /${resource} -> 401`;
});

await step("resource list returns an array with credentials", async () => {
  const response = await fetch(`${base}/${resource}`, { headers: authHeaders() });
  await expect(response, 200, "authenticated list");
  const body = await response.json();
  if (!Array.isArray(body)) throw new Error("list payload was not an array");
  return `GET /${resource} -> 200 (${body.length} item(s))`;
});

await step("create resource from payload", async () => {
  const response = await fetch(`${base}/${resource}`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  await expect(response, 201, "create");
  const body = await response.json();
  if (typeof body.id !== "string" || body.id.length === 0) {
    throw new Error("created entity has no id");
  }
  for (const [key, value] of Object.entries(payload)) {
    if (JSON.stringify(body[key]) !== JSON.stringify(value)) {
      throw new Error(`created entity ${key} was ${JSON.stringify(body[key])}, expected ${JSON.stringify(value)}`);
    }
  }
  createdId = body.id;
  return `POST /${resource} -> 201 (id=${createdId})`;
});

await step("fetch the created resource by id", async () => {
  const response = await fetch(`${base}/${resource}/${createdId}`, { headers: authHeaders() });
  await expect(response, 200, "fetch by id");
  const body = await response.json();
  if (body.id !== createdId) throw new Error(`fetched id ${body.id} != ${createdId}`);
  return `GET /${resource}/${createdId} -> 200`;
});

await step("replace the resource with updated fields", async () => {
  const merged = { ...payload, ...changes };
  const response = await fetch(`${base}/${resource}/${createdId}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(merged),
  });
  await expect(response, 200, "replace");
  const body = await response.json();
  for (const [key, value] of Object.entries(merged)) {
    if (JSON.stringify(body[key]) !== JSON.stringify(value)) {
      throw new Error(`replaced entity ${key} was ${JSON.stringify(body[key])}, expected ${JSON.stringify(value)}`);
    }
  }
  return `PUT /${resource}/${createdId} -> 200`;
});

await step("delete the created resource", async () => {
  const response = await fetch(`${base}/${resource}/${createdId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  await expect(response, 204, "delete");
  return `DELETE /${resource}/${createdId} -> 204`;
});

await step("deleted resource is no longer fetchable", async () => {
  const response = await fetch(`${base}/${resource}/${createdId}`, { headers: authHeaders() });
  await expect(response, 404, "fetch deleted");
  return `GET /${resource}/${createdId} -> 404`;
});

const ok = steps.every((entry) => entry.ok);
process.stdout.write(`${JSON.stringify({ ok, resource, steps }, null, 2)}\\n`);
process.exitCode = ok ? 0 : 1;
"""


def _id_field_name(model: DataModelSpec) -> str | None:
    for field in model.fields:
        if field.name == "id":
            return field.name
    for field in model.fields:
        if field.type is AbstractFieldType.IDENTIFIER:
            return field.name
    return None


class StaticSpaFrontendBackend:
    """Deterministic, model-free compiler backend for a static SPA bundle."""

    backend_id = "static_spa_frontend"

    # -- public: pure product ---------------------------------------------

    def generate(self, system_model: SystemModel) -> CompilationResult:
        slug = slugify(system_model.system_name)
        resources = self._resources(system_model.data_models)
        primary = resources[0]["path"] if resources else "items"
        root = f"{slug}/frontend"
        files: dict[str, str] = {
            f"{root}/package.json": self._package_json(slug),
            f"{root}/index.html": self._index_html(),
            f"{root}/styles.css": self._styles_css(),
            f"{root}/app.js": self._app_js(resources, primary),
            f"{root}/tests/app.test.mjs": self._app_test(resources),
            f"{root}/smoke.mjs": self._smoke_js(primary),
            f"{root}/serve.py": self._serve_py(),
            f"{root}/Dockerfile": self._dockerfile(),
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
            language="javascript",
            required_files=(
                f"{slug}/frontend/index.html",
                f"{slug}/frontend/app.js",
                f"{slug}/frontend/tests/app.test.mjs",
                f"{slug}/frontend/smoke.mjs",
            ),
            verifier_kind="javascript",
            build_command=None,
            test_command=["node", "--test", f"{slug}/frontend/tests/*.mjs"],
            runtime_image=None,
            requires_build_phase=False,
        )

    def declaration(self) -> BackendCapabilityDeclaration:
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.FRONTEND_APPLICATION],
            capabilities=[
                BundleCapability.BUILD,
                BundleCapability.LINT,
                BundleCapability.TEST,
                BundleCapability.DOCUMENTATION,
            ],
            quality_profile=0.8,
            metadata={"language": "javascript", "style": "static-spa"},
        )

    @property
    def name(self) -> str:
        return self.backend_id

    # -- ISR derivation ----------------------------------------------------

    def _resources(self, models: list[DataModelSpec]) -> list[dict]:
        resources: list[dict] = []
        for model in models:
            snake = snake_case(model.name)
            id_name = _id_field_name(model)
            fields: list[dict] = []
            for field in model.fields:
                if id_name is not None and field.name == id_name:
                    continue
                entry = {
                    "name": field.name,
                    "label": field.name.replace("_", " ").title(),
                    "control": _CONTROL_BY_TYPE.get(field.type, "text"),
                    "required": field.required,
                    "options": list(field.enumeration_values),
                }
                fields.append(entry)
            resources.append(
                {
                    "name": model.name,
                    "path": pluralize(snake),
                    "fields": fields,
                }
            )
        return resources

    # -- file generators ---------------------------------------------------

    def _package_json(self, slug: str) -> str:
        payload = {"name": f"{slug}-frontend", "private": True, "type": "module"}
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    def _index_html(self) -> str:
        return "\n".join(
            [
                "<!DOCTYPE html>",
                '<html lang="en">',
                "  <head>",
                '    <meta charset="utf-8" />',
                '    <meta name="viewport" content="width=device-width, initial-scale=1" />',
                "    <title>Generated application</title>",
                '    <link rel="stylesheet" href="styles.css" />',
                "  </head>",
                "  <body>",
                "    <main>",
                "      <h1>Generated application</h1>",
                '      <section class="connection">',
                '        <label>API base <input id="api-base" type="text" value="http://127.0.0.1:8000" /></label>',
                '        <label>API key <input id="api-key" type="password" value="" autocomplete="off" /></label>',
                '        <button id="refresh" type="button">Refresh</button>',
                "      </section>",
                '      <p id="error-banner" role="alert"></p>',
                '      <section class="create">',
                "        <h2>Create</h2>",
                '        <form id="resource-form"></form>',
                "      </section>",
                '      <section class="list">',
                "        <h2>Items</h2>",
                '        <ul id="resource-list"></ul>',
                "      </section>",
                "    </main>",
                '    <script type="module" src="app.js"></script>',
                "  </body>",
                "</html>",
                "",
            ]
        )

    def _styles_css(self) -> str:
        return "\n".join(
            [
                ":root {",
                "  color-scheme: light dark;",
                "  font-family: system-ui, sans-serif;",
                "}",
                "main {",
                "  max-width: 60rem;",
                "  margin: 0 auto;",
                "  padding: 1rem;",
                "}",
                ".connection {",
                "  display: flex;",
                "  gap: 1rem;",
                "  flex-wrap: wrap;",
                "}",
                "#resource-list {",
                "  list-style: none;",
                "  padding: 0;",
                "}",
                "#resource-list li {",
                "  display: flex;",
                "  gap: 0.5rem;",
                "  align-items: center;",
                "  padding: 0.35rem 0;",
                "}",
                "#resource-list li span {",
                "  flex: 1;",
                "}",
                "#error-banner:empty {",
                "  display: none;",
                "}",
                "",
            ]
        )

    def _app_js(self, resources: list[dict], primary: str) -> str:
        return _APP_JS_TEMPLATE.replace(
            "<<RESOURCES>>", json.dumps(resources, indent=2)
        ).replace("<<PRIMARY>>", primary)

    def _app_test(self, resources: list[dict]) -> str:
        fields = [
            field
            for resource in resources
            for field in resource["fields"]
        ]
        if not fields:
            fields = [
                {
                    "name": "id",
                    "control": "text",
                    "required": False,
                    "options": [],
                }
            ]
        return _APP_TEST_TEMPLATE.replace(
            "<<FIELDS>>", json.dumps(fields, indent=2)
        )

    def _smoke_js(self, primary: str) -> str:
        return _SMOKE_JS_TEMPLATE.replace("<<PRIMARY>>", primary)

    def _serve_py(self) -> str:
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "import os",
                "import http.server",
                "import socketserver",
                "from pathlib import Path",
                "",
                "",
                "class SpaRequestHandler(http.server.SimpleHTTPRequestHandler):",
                "    def end_headers(self) -> None:",
                '        self.send_header("Access-Control-Allow-Origin", "*")',
                "        super().end_headers()",
                "",
                "    def send_head(self):",
                "        path = self.translate_path(self.path)",
                '        if not os.path.exists(path) and "." not in self.path.rstrip("/").split("/")[-1]:',
                '            self.path = "/index.html"',
                "        return super().send_head()",
                "",
                "",
                "def main() -> int:",
                '    parser = argparse.ArgumentParser(description="Serve the generated static frontend")',
                '    parser.add_argument("port", nargs="?", type=int, default=8080)',
                "    args = parser.parse_args()",
                "    directory = Path(__file__).resolve().parent",
                "",
                "    class Handler(SpaRequestHandler):",
                "        def __init__(self, *pos, **kw):",
                "            super().__init__(*pos, directory=str(directory), **kw)",
                "",
                "    socketserver.ThreadingTCPServer.allow_reuse_address = True",
                "    with socketserver.ThreadingTCPServer((\"127.0.0.1\", args.port), Handler) as server:",
                "        server.serve_forever()",
                "    return 0",
                "",
                "",
                'if __name__ == "__main__":',
                "    raise SystemExit(main())",
                "",
            ]
        )

    def _dockerfile(self) -> str:
        return "\n".join(
            [
                "FROM python:3.12-slim",
                "WORKDIR /srv",
                "COPY . /srv",
                "EXPOSE 8080",
                'CMD ["python", "serve.py", "8080"]',
                "",
            ]
        )

    def _manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[
                BundleCapability.BUILD,
                BundleCapability.TEST,
                BundleCapability.DOCUMENTATION,
            ],
            metadata={"language": "javascript", "style": "static-spa"},
        )
