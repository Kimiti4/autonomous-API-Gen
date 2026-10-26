"""Elixir HTTP backend.

The generated service uses OTP :gen_tcp and :ets. It does not download Phoenix
or claim authorization, effect execution, or event delivery.
"""
from __future__ import annotations

import json

from compiler.backends._naming import plural as _plural
from compiler.backends._naming import slug as _slug
from compiler.core.capabilities import (
    BackendCapabilities,
    SemanticFeature,
    UnsupportedSemanticsError,
    assert_plan_supported,
)
from compiler.core.declared_api import DeclaredRoute, declared_routes
from compiler.core.conformance import CHECKER, ConformanceReport
from compiler.core.plan import CompilationPlan
from compiler.core.protocol import BackendClass, BackendIdentity, TestSpec
from compiler.core.repository import GeneratedRepository, build_repository
from compiler.core.semantic_obligations import manifest_from_plan


def _elixir_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("#{", "\\#{")
    return f'"{escaped}"'


def _term(value: object) -> str:
    if isinstance(value, str):
        return _elixir_string(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "nil"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, tuple):
        return "{" + ", ".join(_term(item) for item in value) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_term(item) for item in value) + "]"
    if isinstance(value, dict):
        body = ", ".join(f"{_term(key)} => {_term(item)}" for key, item in value.items())
        return "%{" + body + "}"
    raise TypeError(f"cannot encode {type(value).__name__} for Elixir")


def _key_name(routes: tuple[DeclaredRoute, ...]) -> str:
    return next(route.path_fields[0].name for route in routes if route.path_fields)


def _field_specs(fields: tuple) -> list[tuple]:
    return [
        (field.name, field.value_type.value, field.required, field.precision, field.scale)
        for field in fields
    ]


def _policy_rules(route: DeclaredRoute) -> list[dict]:
    rules = []
    for policy in route.policies:
        assert policy.behavior is not None
        for rule in policy.behavior.rules:
            if rule.resource not in (route.resource, "*"):
                continue
            if "*" not in rule.actions and route.action not in rule.actions:
                continue
            rules.append({
                "effect": rule.effect,
                "roles": list(rule.roles),
                "actions": list(rule.actions),
                "resource": rule.resource,
            })
    return rules


class ElixirPhoenixBackend:
    name = "elixir-phoenix"
    language = "elixir"
    framework = "otp-http"
    version = "1.0.0"
    supported_features = frozenset({
        SemanticFeature.API_CONTRACTS,
        SemanticFeature.AUTHORIZATION_POLICIES,
        SemanticFeature.EFFECT_POLICY_PRESERVATION,
        SemanticFeature.EFFECT_BINDING_PRESERVATION,
        SemanticFeature.CONSEQUENCE_PRESERVATION,
    })
    _DECLARED_TYPES = frozenset({"string", "identifier", "integer", "decimal", "money", "boolean"})

    def identity(self) -> BackendIdentity:
        return BackendIdentity(
            name=self.name, language=self.language, framework=self.framework,
            version=self.version, backend_class=BackendClass.BEHAVIORAL,
        )

    def test_spec(self) -> TestSpec:
        return TestSpec(command=["mix", "test"], runs_in="runtime")

    def element_paths(self, plan: CompilationPlan) -> dict[str, str]:
        paths: dict[str, str] = {}
        for service in plan.services:
            paths[service.id] = f"lib/esap/{_slug(service.name).lower()}.ex"
            for model in service.data_models:
                paths[model.id] = f"lib/esap/{_slug(model.entity_name).lower()}.ex"
            for event in service.published_events + service.consumed_events:
                paths[event.id] = f"lib/esap/event_{_slug(event.name).lower()}.ex"
        for policy in plan.security:
            paths[policy.policy_id] = "lib/esap/security.ex"
        paths.update({
            "infra:docker": "Dockerfile",
            "infra:k8s": "k8s/deployment.yaml",
            "infra:ci": ".github/workflows/ci.yml",
            "infra:readme": "README.md",
            "infra:main": "lib/esap/server.ex",
            "infra:repositories": "lib/esap/repository.ex",
            "infra:docs": "docs/architecture.md",
            "infra:semantic_obligations": "docs/semantic-obligations.json",
        })
        return paths

    def compile(self, plan: CompilationPlan) -> GeneratedRepository:
        assert_plan_supported(plan, BackendCapabilities(
            backend_id=self.name, version=self.version, supported_features=self.supported_features,
        ))
        self._assert_declared_slice(declared_routes(plan))
        files = {path: self._emit(path, plan) for path in dict.fromkeys(self.element_paths(plan).values())}
        files["mix.exs"] = self._mix()
        files["test/test_helper.exs"] = "ExUnit.start()\n"
        files["test/esap_test.exs"] = self._test(plan)
        return build_repository(files)

    def conformance(self, plan: CompilationPlan, repo: GeneratedRepository) -> ConformanceReport:
        return CHECKER.check(plan, self.element_paths(plan), repo)

    def _entities(self, plan: CompilationPlan) -> list[tuple[str, str, str]]:
        found = []
        for service in plan.services:
            for model in service.data_models:
                slug = _slug(model.entity_name)
                found.append((slug, slug.lower(), _plural(slug)))
        return found

    def _emit(self, path: str, plan: CompilationPlan) -> str:
        if path == "lib/esap/server.ex":
            return self._server(plan)
        if path == "lib/esap/repository.ex":
            return (
                "defmodule Esap.Repository do\n"
                "  @moduledoc \"ETS tables owned by the process that starts the server.\"\n"
                "  def own do\n"
                + "".join(
                    f"    Esap.{name}.own()\n" for name, _, _ in self._entities(plan)
                )
                + ("    Esap.Declared.own()\n" if declared_routes(plan) else "")
                + "    :ok\n  end\nend\n"
            )
        if path == "docs/semantic-obligations.json":
            return json.dumps(manifest_from_plan(plan), sort_keys=True, indent=2)
        if path == "Dockerfile":
            return "FROM elixir:1.18\nWORKDIR /app\nCOPY . .\nRUN mix test\n"
        if path == "k8s/deployment.yaml":
            return (
                "# This manifest is not applied by the compiler.\n"
                "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: esap-elixir-unproven\n"
                "data:\n  status: not-deployed\n"
            )
        if path == ".github/workflows/ci.yml":
            return "name: elixir\non: [workflow_dispatch]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: mix test\n"
        if path == "README.md":
            return "# Generated Elixir service\n\nRun `mix test`. This service does not enforce authorization or execute effects.\n"
        if path == "docs/architecture.md":
            return "# Architecture\n\nOTP :gen_tcp serves JSON over an ETS store. Phoenix is not a dependency.\n"
        if path == "lib/esap/security.ex":
            return "defmodule Esap.Security do\n  @moduledoc \"Security policies are preserved only. This module grants nothing.\"\n  def authorize(_role, _action), do: false\nend\n"
        if path.startswith("lib/esap/event_"):
            return "defmodule Esap.UnusedEvent do\n  @moduledoc \"Event delivery is not implemented.\"\n  def deliver(_payload), do: {:error, :unsupported}\nend\n"
        name = path.rsplit("/", 1)[-1].removesuffix(".ex")
        for label, module, _plural in self._entities(plan):
            if module == name:
                return self._entity(label)
        return "defmodule Esap.Service do\n  @moduledoc \"Generated service boundary. Records live in entity modules.\"\n  def ready?, do: true\nend\n"

    def _entity(self, name: str) -> str:
        return (
            f"defmodule Esap.{name} do\n"
            f"  @table :esap_{name.lower()}\n"
            "  def own do\n"
            "    case :ets.whereis(@table) do\n"
            "      :undefined -> :ets.new(@table, [:named_table, :public, :set])\n"
            "      _ -> :ets.delete_all_objects(@table)\n"
            "    end\n"
            "    :ok\n"
            "  end\n"
            "  def create(attrs) when is_map(attrs) do\n"
            "    id = Map.get(attrs, \"id\") || Integer.to_string(System.unique_integer([:positive]))\n"
            "    row = Map.put(attrs, \"id\", id)\n"
            "    :ets.insert(@table, {id, row})\n"
            "    {:ok, row}\n"
            "  end\n"
            "  def fetch(id) when is_binary(id) do\n"
            "    case :ets.lookup(@table, id) do\n"
            "      [{^id, row}] -> {:ok, row}\n"
            "      [] -> :error\n"
            "    end\n"
            "  end\n"
            "end\n"
        )

    def _assert_declared_slice(self, routes: tuple[DeclaredRoute, ...]) -> None:
        from compiler.core.isr_parity import assert_contract_slice
        assert_contract_slice(routes)

    def _server(self, plan: CompilationPlan) -> str:
        routes = declared_routes(plan)
        if routes:
            return self._declared_server(routes, require_api_key=bool(plan.security))
        clauses = []
        for name, _module, plural in self._entities(plan):
            clauses.append(
                f"  defp dispatch(\"POST\", \"/api/{plural}\", body) do\n"
                f"    case Esap.{name}.create(:json.decode(body)) do\n"
                "      {:ok, row} -> {201, row}\n"
                "    end\n"
                "  end\n"
                f"  defp dispatch(\"GET\", \"/api/{plural}/\" <> id, _body) do\n"
                f"    case Esap.{name}.fetch(id) do\n"
                "      {:ok, row} -> {200, row}\n"
                "      :error -> {404, %{\"error\" => \"not_found\"}}\n"
                "    end\n"
                "  end\n"
            )
        return (
            "defmodule Esap.Server do\n"
            "  def start(port \\\\ 0) do\n"
            "    Esap.Repository.own()\n"
            "    {:ok, listen} = :gen_tcp.listen(port, [:binary, packet: :raw, active: false, reuseaddr: true])\n"
            "    {:ok, actual} = :inet.port(listen)\n"
            "    pid = spawn_link(fn -> accept(listen) end)\n"
            "    %{listen: listen, port: actual, pid: pid}\n"
            "  end\n"
            "  def stop(server) do\n"
            "    Process.exit(server.pid, :kill)\n"
            "    :gen_tcp.close(server.listen)\n"
            "  end\n"
            "  defp accept(listen) do\n"
            "    case :gen_tcp.accept(listen) do\n"
            "      {:ok, sock} -> spawn(fn -> handle(sock) end); accept(listen)\n"
            "      {:error, :closed} -> :ok\n"
            "      {:error, _} -> :ok\n"
            "    end\n"
            "  end\n"
            "  defp handle(sock) do\n"
            "    {:ok, raw} = read_request(sock, \"\")\n"
            "    [head, rest] = String.split(raw, \"\\r\\n\\r\\n\", parts: 2)\n"
            "    [request | headers] = String.split(head, \"\\r\\n\")\n"
            "    [method, path | _] = String.split(request, \" \")\n"
            "    path = path |> String.split(\"?\", parts: 2) |> hd()\n"
            "    body = read_body(sock, rest, content_length(headers))\n"
            "    {status, payload} = dispatch(method, path, body)\n"
            "    encoded = IO.iodata_to_binary(:json.encode(payload))\n"
            "    :gen_tcp.send(sock, [\n"
            "      \"HTTP/1.1 \", Integer.to_string(status), \" OK\\r\\n\",\n"
            "      \"content-type: application/json\\r\\n\",\n"
            "      \"content-length: \", Integer.to_string(byte_size(encoded)), \"\\r\\n\\r\\n\",\n"
            "      encoded\n"
            "    ])\n"
            "    :gen_tcp.close(sock)\n"
            "  end\n"
            "  defp read_request(sock, acc) do\n"
            "    if String.contains?(acc, \"\\r\\n\\r\\n\") do\n"
            "      {:ok, acc}\n"
            "    else\n"
            "      {:ok, chunk} = :gen_tcp.recv(sock, 0, 2_000)\n"
            "      read_request(sock, acc <> chunk)\n"
            "    end\n"
            "  end\n"
            "  defp content_length(headers) do\n"
            "    Enum.find_value(headers, 0, fn header ->\n"
            "      if String.downcase(header) |> String.starts_with?(\"content-length:\") do\n"
            "        header |> String.split(\":\", parts: 2) |> Enum.at(1) |> String.trim() |> String.to_integer()\n"
            "      end\n"
            "    end)\n"
            "  end\n"
            "  defp read_body(_sock, have, length) when byte_size(have) >= length, do: binary_part(have, 0, length)\n"
            "  defp read_body(sock, have, length) do\n"
            "    {:ok, chunk} = :gen_tcp.recv(sock, 0, 2_000)\n"
            "    read_body(sock, have <> chunk, length)\n"
            "  end\n"
            "  defp dispatch(\"GET\", \"/health\", _body), do: {200, %{\"status\" => \"ok\"}}\n"
            + "".join(clauses)
            + "  defp dispatch(_method, _path, _body), do: {404, %{\"error\" => \"not_found\"}}\n"
            "end\n"
        )

    def _declared_server(self, routes: tuple[DeclaredRoute, ...], *, require_api_key: bool) -> str:
        paths: dict[str, dict[str, dict]] = {"/health": {"get": {}}}
        for route in routes:
            paths.setdefault(route.path, {})[route.method.lower()] = {}
        clauses = [
            "  defp dispatch(\"GET\", \"/openapi.json\", _headers, _body) do\n"
            "    {200, %{\"paths\" => " + _term(paths) + "}}\n"
            "  end\n",
            "  defp dispatch(\"GET\", \"/health\", _headers, _body), do: {200, %{\"status\" => \"ok\"}}\n",
        ]
        for route in routes:
            action = _elixir_string(route.action)
            names = _term([field.name for field in route.response_fields])
            if route.method == "POST":
                spec = _term(_field_specs(route.body_fields))
                clauses.append(
                    f"  defp dispatch(\"POST\", {_elixir_string(route.path)}, headers, body) do\n"
                    f"    with_auth(headers, {action}, fn ->\n"
                    "      case decode_object(body) do\n"
                    f"        {{:ok, data}} -> case validate(data, {spec}) do\n"
                    "          :ok ->\n"
                    f"            :ets.insert(@table, {{Map.fetch!(data, {_elixir_string(_key_name(routes))}), data}})\n"
                    f"            {{201, project(data, {names})}}\n"
                    "          :error -> {422, %{\"detail\" => \"validation\"}}\n"
                    "        end\n"
                    "        :error -> {422, %{\"detail\" => \"validation\"}}\n"
                    "      end\n"
                    "    end)\n"
                    "  end\n"
                )
            else:
                prefix = route.path.split("{", 1)[0]
                verb = route.method
                success = "200"
                body = (
                    "      case :ets.lookup(@table, id) do\n"
                    f"        [{{^id, row}}] -> {{{success}, project(row, {names})}}\n"
                    "        [] -> {404, %{\"error\" => \"not_found\"}}\n"
                    "      end\n"
                )
                if verb == "DELETE":
                    body = (
                        "      case :ets.lookup(@table, id) do\n"
                        "        [{^id, row}] ->\n"
                        "          :ets.delete(@table, id)\n"
                        f"          {{200, project(row, {names})}}\n"
                        "        [] -> {404, %{\"error\" => \"not_found\"}}\n"
                        "      end\n"
                    )
                clauses.append(
                    f"  defp dispatch({_elixir_string(verb)}, {_elixir_string(prefix)} <> id, headers, _body) do\n"
                    "    if String.contains?(id, \"/\") do\n"
                    "      {404, %{\"error\" => \"not_found\"}}\n"
                    "    else\n"
                    f"      with_auth(headers, {action}, fn ->\n"
                    f"{body}"
                    "      end)\n"
                    "    end\n"
                    "  end\n"
                )
        rule_clauses = []
        seen_actions: set[str] = set()
        for route in routes:
            if route.action in seen_actions:
                continue
            seen_actions.add(route.action)
            rule_clauses.append(
                f"  defp rules({_elixir_string(route.action)}), do: {_term(_policy_rules(route))}\n"
            )
        flag = "true" if require_api_key else "false"
        return (
            "defmodule Esap.Declared do\n"
            "  @table :esap_declared\n"
            "  def own do\n"
            "    case :ets.whereis(@table) do\n"
            "      :undefined -> :ets.new(@table, [:named_table, :public, :set])\n"
            "      _ -> :ets.delete_all_objects(@table)\n"
            "    end\n"
            "    :ok\n"
            "  end\n"
            "end\n"
            "defmodule Esap.Server do\n"
            "  @table :esap_declared\n"
            f"  @require_api_key {flag}\n"
            "  def start(port \\\\ 0) do\n"
            "    Esap.Repository.own()\n"
            "    {:ok, listen} = :gen_tcp.listen(port, [:binary, packet: :raw, active: false, reuseaddr: true])\n"
            "    {:ok, actual} = :inet.port(listen)\n"
            "    pid = spawn_link(fn -> accept(listen) end)\n"
            "    %{listen: listen, port: actual, pid: pid}\n"
            "  end\n"
            "  def stop(server) do\n"
            "    Process.exit(server.pid, :kill)\n"
            "    :gen_tcp.close(server.listen)\n"
            "  end\n"
            "  defp accept(listen) do\n"
            "    case :gen_tcp.accept(listen) do\n"
            "      {:ok, sock} -> spawn(fn -> handle(sock) end); accept(listen)\n"
            "      {:error, :closed} -> :ok\n"
            "      {:error, _} -> :ok\n"
            "    end\n"
            "  end\n"
            "  defp handle(sock) do\n"
            "    {:ok, raw} = read_request(sock, \"\")\n"
            "    [head, rest] = String.split(raw, \"\\r\\n\\r\\n\", parts: 2)\n"
            "    [request | headers] = String.split(head, \"\\r\\n\")\n"
            "    [method, path | _] = String.split(request, \" \")\n"
            "    path = path |> String.split(\"?\", parts: 2) |> hd()\n"
            "    body = read_body(sock, rest, content_length(headers))\n"
            "    {status, payload} = dispatch(method, path, headers, body)\n"
            "    encoded = IO.iodata_to_binary(:json.encode(payload))\n"
            "    :gen_tcp.send(sock, [\n"
            "      \"HTTP/1.1 \", Integer.to_string(status), \" OK\\r\\n\",\n"
            "      \"content-type: application/json\\r\\n\",\n"
            "      \"content-length: \", Integer.to_string(byte_size(encoded)), \"\\r\\n\\r\\n\",\n"
            "      encoded\n"
            "    ])\n"
            "    :gen_tcp.close(sock)\n"
            "  end\n"
            "  defp read_request(sock, acc) do\n"
            "    if String.contains?(acc, \"\\r\\n\\r\\n\"), do: {:ok, acc}, else: (\n"
            "      {:ok, chunk} = :gen_tcp.recv(sock, 0, 2_000); read_request(sock, acc <> chunk))\n"
            "  end\n"
            "  defp content_length(headers) do\n"
            "    Enum.find_value(headers, 0, fn header ->\n"
            "      if String.downcase(header) |> String.starts_with?(\"content-length:\") do\n"
            "        header |> String.split(\":\", parts: 2) |> Enum.at(1) |> String.trim() |> String.to_integer()\n"
            "      end\n"
            "    end)\n"
            "  end\n"
            "  defp read_body(_sock, have, length) when byte_size(have) >= length, do: binary_part(have, 0, length)\n"
            "  defp read_body(sock, have, length) do\n"
            "    {:ok, chunk} = :gen_tcp.recv(sock, 0, 2_000)\n"
            "    read_body(sock, have <> chunk, length)\n"
            "  end\n"
            + "".join(clauses)
            + "  defp dispatch(_method, _path, _headers, _body), do: {404, %{\"error\" => \"not_found\"}}\n"
            "  defp with_auth(headers, action, fun) do\n"
            "    case gate(headers, action) do\n"
            "      :ok -> fun.()\n"
            "      {:error, status, payload} -> {status, payload}\n"
            "    end\n"
            "  end\n"
            "  defp gate(headers, action) do\n"
            "    with :ok <- check_api_key(headers), {:ok, roles} <- principal_roles(headers) do\n"
            "      if allowed?(rules(action), roles, action), do: :ok, else: {:error, 403, %{\"detail\" => \"unauthorized\"}}\n"
            "    end\n"
            "  end\n"
            "  defp check_api_key(_headers) when not @require_api_key, do: :ok\n"
            "  defp check_api_key(headers) do\n"
            "    expected = System.get_env(\"GENERATED_API_KEY\") || \"\"\n"
            "    presented = header_value(headers, \"x-api-key\") || \"\"\n"
            "    cond do\n"
            "      expected == \"\" -> {:error, 503, %{\"detail\" => \"GENERATED_API_KEY is not configured\"}}\n"
            "      byte_size(expected) == byte_size(presented) and :crypto.hash_equals(expected, presented) -> :ok\n"
            "      true -> {:error, 401, %{\"detail\" => \"invalid api key\"}}\n"
            "    end\n"
            "  end\n"
            "  defp principal_roles(headers) do\n"
            "    secret = System.get_env(\"GENERATED_AUTH_SECRET\") || \"\"\n"
            "    header = header_value(headers, \"authorization\") || \"\"\n"
            "    cond do\n"
            "      secret == \"\" -> {:error, 503, %{\"detail\" => \"GENERATED_AUTH_SECRET is not configured\"}}\n"
            "      not String.starts_with?(String.downcase(header), \"bearer \") -> {:error, 401, %{\"detail\" => \"bearer token required\"}}\n"
            "      true -> verify_token(secret, header |> String.split(\" \", parts: 2) |> Enum.at(1) |> String.trim())\n"
            "    end\n"
            "  end\n"
            "  defp verify_token(secret, token) do\n"
            "    case String.split(token, \".\", parts: 2) do\n"
            "      [body, signature] ->\n"
            "        mac = :crypto.mac(:hmac, :sha256, secret, body)\n"
            "        with {:ok, raw_sig} <- decode64(signature),\n"
            "             true <- byte_size(mac) == byte_size(raw_sig),\n"
            "             true <- :crypto.hash_equals(mac, raw_sig),\n"
            "             {:ok, claims} <- decode_claims(body),\n"
            "             true <- is_integer(claims[\"exp\"]) and claims[\"exp\"] >= System.system_time(:second),\n"
            "             true <- is_binary(claims[\"sub\"]) and claims[\"sub\"] != \"\",\n"
            "             true <- is_list(claims[\"roles\"]) do\n"
            "          {:ok, claims[\"roles\"]}\n"
            "        else\n"
            "          _ -> {:error, 401, %{\"detail\" => \"invalid token\"}}\n"
            "        end\n"
            "      _ -> {:error, 401, %{\"detail\" => \"malformed token\"}}\n"
            "    end\n"
            "  end\n"
            "  defp decode_claims(body) do\n"
            "    with {:ok, raw} <- decode64(body), {:ok, claims} when is_map(claims) <- decode_json(raw) do\n"
            "      {:ok, claims}\n"
            "    else\n"
            "      _ -> :error\n"
            "    end\n"
            "  end\n"
            "  defp decode_json(raw) do\n"
            "    {:ok, :json.decode(raw)}\n"
            "  rescue\n"
            "    _ -> :error\n"
            "  end\n"
            "  defp decode64(text) do\n"
            "    pad = rem(4 - rem(byte_size(text), 4), 4)\n"
            "    Base.url_decode64(text <> String.duplicate(\"=\", pad))\n"
            "  end\n"
            "  defp header_value(headers, name) do\n"
            "    Enum.find_value(headers, fn header ->\n"
            "      case String.split(header, \":\", parts: 2) do\n"
            "        [key, value] -> if String.downcase(String.trim(key)) == name, do: String.trim(value), else: nil\n"
            "        _ -> nil\n"
            "      end\n"
            "    end)\n"
            "  end\n"
            + "".join(rule_clauses)
            + "  defp rules(_action), do: []\n"
            "  defp allowed?(rules, roles, action) do\n"
            "    cond do\n"
            "      Enum.any?(rules, fn rule -> rule[\"effect\"] == \"deny\" and rule_match?(rule, roles, action) end) -> false\n"
            "      Enum.any?(rules, fn rule -> rule[\"effect\"] == \"allow\" and rule_match?(rule, roles, action) end) -> true\n"
            "      true -> false\n"
            "    end\n"
            "  end\n"
            "  defp rule_match?(rule, roles, action) do\n"
            "    actions = rule[\"actions\"]\n"
            "    (\"*\" in actions or action in actions) and Enum.any?(rule[\"roles\"], &(&1 in roles))\n"
            "  end\n"
            "  defp validate(data, specs) when is_map(data) do\n"
            "    names = Enum.map(specs, fn {name, _, _, _, _} -> name end)\n"
            "    missing = Enum.filter(specs, fn {name, _, required, _, _} -> required and not Map.has_key?(data, name) end)\n"
            "    cond do\n"
            "      Map.keys(data) -- names != [] -> :error\n"
            "      missing != [] -> :error\n"
            "      Enum.all?(specs, fn {name, type, _, precision, scale} ->\n"
            "        case Map.fetch(data, name) do\n"
            "          :error -> true\n"
            "          {:ok, value} -> valid?(type, value, precision, scale)\n"
            "        end\n"
            "      end) -> :ok\n"
            "      true -> :error\n"
            "    end\n"
            "  end\n"
            "  defp validate(_, _), do: :error\n"
            "  defp valid?(\"money\", value, precision, scale) when is_binary(value), do: decimal?(value, precision, scale)\n"
            "  defp valid?(\"decimal\", value, precision, scale) when is_binary(value), do: decimal?(value, precision, scale)\n"
            "  defp valid?(\"identifier\", value, _, _) when is_binary(value), do: value != \"\"\n"
            "  defp valid?(\"string\", value, _, _) when is_binary(value), do: true\n"
            "  defp valid?(\"integer\", value, _, _) when is_integer(value), do: true\n"
            "  defp valid?(\"boolean\", value, _, _) when is_boolean(value), do: true\n"
            "  defp valid?(_, _, _, _), do: false\n"
            "  defp decimal?(value, precision, scale) do\n"
            "    case Regex.run(~r/\\A(-?)(\\d+)(?:\\.(\\d+))?\\z/, value) do\n"
            "      [_, _, whole, frac] ->\n"
            "        digits = byte_size(whole) + byte_size(frac)\n"
            "        (precision == nil or digits <= precision) and (scale == nil or byte_size(frac) <= scale)\n"
            "      [_, _, whole] -> precision == nil or byte_size(whole) <= precision\n"
            "      _ -> false\n"
            "    end\n"
            "  end\n"
            "  defp decode_object(body) when is_binary(body) and body != \"\" do\n"
            "    case decode_json(body) do\n"
            "      {:ok, data} when is_map(data) -> {:ok, data}\n"
            "      _ -> :error\n"
            "    end\n"
            "  end\n"
            "  defp decode_object(_), do: :error\n"
            "  defp project(record, names), do: Map.take(record, names)\n"
            "end\n"
        )

    def _mix(self) -> str:
        return (
            "defmodule Esap.MixProject do\n"
            "  use Mix.Project\n"
            "  def project, do: [app: :esap_app, version: \"0.1.0\", elixir: \"~> 1.18\", deps: deps()]\n"
            "  def application, do: [extra_applications: [:logger, :crypto]]\n"
            "  defp deps, do: []\n"
            "end\n"
        )

    def _test(self, plan: CompilationPlan) -> str:
        entities = [] if declared_routes(plan) else self._entities(plan)
        lines = ["defmodule EsapTest do\n", "  use ExUnit.Case, async: false\n"]
        if entities:
            name, _module, plural = entities[0]
            lines.append(
                f"  test \"create and fetch {plural}\" do\n"
                "    server = Esap.Server.start()\n"
                "    on_exit(fn -> Esap.Server.stop(server) end)\n"
                f"    created = request(server.port, \"POST\", \"/api/{plural}\", ~s({{\"name\":\"Ada\"}}))\n"
                "    assert created.status == 201\n"
                "    assert created.body[\"name\"] == \"Ada\"\n"
                "    id = created.body[\"id\"]\n"
                f"    loaded = request(server.port, \"GET\", \"/api/{plural}/\" <> id, \"\")\n"
                "    assert loaded.status == 200\n"
                "    assert loaded.body[\"name\"] == \"Ada\"\n"
                f"    missing = request(server.port, \"GET\", \"/api/{plural}/missing\", \"\")\n"
                "    assert missing.status == 404\n"
                "  end\n"
            )
        lines.append(
            "  test \"health responds\" do\n"
            "    server = Esap.Server.start()\n"
            "    on_exit(fn -> Esap.Server.stop(server) end)\n"
            "    assert request(server.port, \"GET\", \"/health\", \"\").body[\"status\"] == \"ok\"\n"
            "  end\n"
            "  defp request(port, method, path, body) do\n"
            "    {:ok, sock} = :gen_tcp.connect(~c\"127.0.0.1\", port, [:binary, active: false])\n"
            "    :gen_tcp.send(sock, [\n"
            "      method, \" \", path, \" HTTP/1.1\\r\\nHost: localhost\\r\\nContent-Length: \",\n"
            "      Integer.to_string(byte_size(body)), \"\\r\\n\\r\\n\", body\n"
            "    ])\n"
            "    {:ok, raw} = recv(sock, \"\")\n"
            "    :gen_tcp.close(sock)\n"
            "    [head, rest] = String.split(raw, \"\\r\\n\\r\\n\", parts: 2)\n"
            "    [status_line | headers] = String.split(head, \"\\r\\n\")\n"
            "    [_, code | _] = String.split(status_line, \" \")\n"
            "    length = Enum.find_value(headers, 0, fn header ->\n"
            "      if String.starts_with?(String.downcase(header), \"content-length:\") do\n"
            "        header |> String.split(\":\", parts: 2) |> Enum.at(1) |> String.trim() |> String.to_integer()\n"
            "      end\n"
            "    end)\n"
            "    payload = if byte_size(rest) >= length, do: binary_part(rest, 0, length), else: rest\n"
            "    %{status: String.to_integer(code), body: :json.decode(payload)}\n"
            "  end\n"
            "  defp recv(sock, acc) do\n"
            "    if String.contains?(acc, \"\\r\\n\\r\\n\") and body_complete?(acc) do\n"
            "      {:ok, acc}\n"
            "    else\n"
            "      case :gen_tcp.recv(sock, 0, 2_000) do\n"
            "        {:ok, chunk} -> recv(sock, acc <> chunk)\n"
            "        {:error, :closed} -> {:ok, acc}\n"
            "      end\n"
            "    end\n"
            "  end\n"
            "  defp body_complete?(raw) do\n"
            "    if not String.contains?(raw, \"\\r\\n\\r\\n\"), do: false, else: (\n"
            "      [head, rest] = String.split(raw, \"\\r\\n\\r\\n\", parts: 2)\n"
            "      [_ | headers] = String.split(head, \"\\r\\n\")\n"
            "      length = Enum.find_value(headers, 0, fn header ->\n"
            "        if String.starts_with?(String.downcase(header), \"content-length:\") do\n"
            "          header |> String.split(\":\", parts: 2) |> Enum.at(1) |> String.trim() |> String.to_integer()\n"
            "        end\n"
            "      end)\n"
            "      byte_size(rest) >= length\n"
            "    )\n"
            "  end\n"
            "end\n"
        )
        return "".join(lines)
