"""RustAxumBackend — second reference backend: Rust + Axum (ADR-012 + runnability upgrade).

Emits a genuinely runnable Axum application: health endpoint, per-entity CRUD
handlers wired through application validation and an in-memory store, typed
domain models, event handlers, fail-closed API-key authorization, a served
OpenAPI document, working Kubernetes/CI manifests, multi-stage Dockerfile, and
a real tokio test suite exercising CRUD, auth, and event validation. Module
wiring (mod.rs) guarantees every emitted file is actually compiled — no dead
placeholder modules.
"""
from __future__ import annotations
import json

from compiler.core.plan import CompilationPlan
from compiler.core.capabilities import BackendCapabilities, SemanticFeature, assert_plan_supported
from compiler.core.repository import GeneratedRepository, build_repository
from compiler.core.conformance import CHECKER, ConformanceReport
from compiler.core.protocol import BackendClass, BackendIdentity, TestSpec
from compiler.backends._naming import (
    plan_entities,
    plan_events,
    plan_services,
    plural as _plural,
    slug as _slug,
    cls_name as _cls,
)


class RustAxumBackend:
    name = "rust-axum"
    language = "rust"
    framework = "axum"
    version = "1.4.0"
    supported_features = frozenset({
        SemanticFeature.TYPED_FIELDS,
        SemanticFeature.DECIMAL_SHAPE,
        SemanticFeature.EXPRESSIONS,
        SemanticFeature.BUSINESS_RULES,
        SemanticFeature.STATE_TRANSITIONS,
    })

    def identity(self) -> BackendIdentity:
        return BackendIdentity(
            name=self.name, language=self.language, framework=self.framework,
            version=self.version, backend_class=BackendClass.BEHAVIORAL,
        )

    def test_spec(self) -> TestSpec:
        return TestSpec(command=["cargo", "test"], runs_in="build", build_target="build")

    def test_image(self, tag: str) -> str:
        """Rust multi-stage: test in the build stage, not the slim runtime image."""
        return f"{tag}-build"

    # -- plan layout -------------------------------------------------------

    def element_paths(self, plan: CompilationPlan) -> dict[str, str]:
        p: dict[str, str] = {}
        for s in plan.services:
            n = _slug(s.name)
            p[s.id] = f"src/application/{n}.rs"
            for mp in s.data_models:
                p[mp.id] = f"src/domain/{_slug(mp.entity_name)}.rs"
            for ev in s.published_events + s.consumed_events:
                p[ev.id] = f"src/events/{_slug(ev.name)}.rs"
        for sp in plan.security:
            p[sp.policy_id] = "src/core/security.rs"
        for effect in plan.effects:
            p[effect.id] = f"src/effects/{_slug(effect.name)}.rs"
        p.update({
            "infra:docker": "Dockerfile",
            "infra:cargo": "Cargo.toml",
            "infra:k8s": "k8s/deployment.yaml",
            "infra:ci": ".github/workflows/ci.yml",
            "infra:readme": "README.md",
            "infra:main": "src/main.rs",
            "infra:repositories": "src/infrastructure/repositories.rs",
            "infra:behavior": "src/core/behavior.rs",
            "infra:docs": "docs/architecture.md",
            "infra:openapi": "openapi.json",
        })
        return p

    def compile(self, plan: CompilationPlan) -> GeneratedRepository:
        assert_plan_supported(plan, BackendCapabilities(backend_id=self.name, version=self.version, supported_features=self.supported_features))
        f: dict[str, str] = {}
        for path in dict.fromkeys(self.element_paths(plan).values()):
            f[path] = self._emit(path, plan)
        # Module wiring: every emitted module is declared, so cargo compiles
        # (and the test suite runs) every file — nothing stays dead.
        entities = plan_entities(plan)
        services = plan_services(plan)
        events = plan_events(plan)

        def mod_rs(stem: str, mods: list[str], empty: str) -> str:
            if not mods:
                return f"//! {empty}\n"
            return f"//! {stem} modules (generated).\n" + "".join(
                f"pub mod {m};\n" for m in mods
            )

        f["src/domain/mod.rs"] = mod_rs(
            "domain", [e["mod"] for e in entities], "No domain modules."
        )
        f["src/application/mod.rs"] = mod_rs(
            "application", [s["mod"] for s in services], "No application modules."
        )
        f["src/events/mod.rs"] = mod_rs(
            "event", [e["mod"] for e in events], "No event modules."
        )
        f["src/effects/mod.rs"] = mod_rs(
            "effect", [_slug(effect.name) for effect in plan.effects], "No effect modules."
        )
        f["src/infrastructure/mod.rs"] = "pub mod repositories;\n"
        f["src/core/mod.rs"] = "pub mod behavior;\n" + ("pub mod security;\n" if plan.security else "")
        return build_repository(f)

    def conformance(self, plan: CompilationPlan, repo: GeneratedRepository) -> ConformanceReport:
        return CHECKER.check(plan, self.element_paths(plan), repo)

    def _secured(self, plan: CompilationPlan) -> bool:
        return bool(plan.security)

    # -- emitters ----------------------------------------------------------

    def _emit(self, path: str, plan: CompilationPlan) -> str:
        if path == "Dockerfile":
            return self._dockerfile()
        if path == "Cargo.toml":
            return self._cargo()
        if path == "src/main.rs":
            return self._main(plan)
        if path == "src/infrastructure/repositories.rs":
            return self._repositories()
        if path == "src/core/security.rs":
            return self._security()
        if path == "src/core/behavior.rs":
            return self._behavior_runtime()
        if path.startswith("src/effects/") and path != "src/effects/mod.rs":
            return self._effect(path, plan)
        if path == "k8s/deployment.yaml":
            return self._k8s()
        if path == ".github/workflows/ci.yml":
            return self._ci()
        if path == "README.md":
            return self._readme(plan)
        if path == "docs/architecture.md":
            return self._docs(plan)
        if path == "openapi.json":
            return self._openapi(plan)
        if path.startswith("src/domain/"):
            return self._domain(path, plan)
        if path.startswith("src/application/"):
            return self._application(path, plan)
        if path.startswith("src/events/"):
            return self._event(path, plan)
        return f"// unrecognised element path: {path}\n"

    def _dockerfile(self) -> str:
        return (
            "FROM rust:1.85-slim AS build\n"
            "WORKDIR /app\n"
            "COPY . .\n"
            "RUN cargo test\n"
            "RUN cargo build --release\n\n"
            "FROM debian:bookworm-slim\n"
            "COPY --from=build /app/target/release/generated /usr/local/bin/app\n"
            "EXPOSE 8000\n"
            "ENV GENERATED_API_KEY=generated-dev-key\n"
            'CMD ["app"]\n'
        )

    def _cargo(self) -> str:
        return (
            "[package]\n"
            'name = "generated"\n'
            'version = "0.1.0"\n'
            'edition = "2021"\n\n'
            "[dependencies]\n"
            'axum = "0.7"\n'
            'tokio = { version = "1", features = ["full"] }\n'
            'serde = { version = "1", features = ["derive"] }\n'
            'serde_json = "1"\n'
            'rust_decimal = { version = "1", features = ["serde"] }\n'
        )

    def _repositories(self) -> str:
        return (
            "//! In-memory store backing the generated application.\n"
            "use serde_json::Value;\n"
            "use std::collections::HashMap;\n\n"
            "#[derive(Default)]\n"
            "pub struct Stores {\n"
            "    items: HashMap<String, Vec<Value>>,\n"
            "}\n\n"
            "impl Stores {\n"
            "    pub fn create(&mut self, entity: &str, payload: Value) -> Value {\n"
            "        let store = self.items.entry(entity.to_string()).or_default();\n"
            "        let mut record = payload;\n"
            "        let needs_id = record\n"
            '            .get("id")\n'
            "            .map(|v| v.is_null())\n"
            "            .unwrap_or(true);\n"
            "        if needs_id {\n"
            "            let next = (store.len() + 1).to_string();\n"
            '            if let Some(obj) = record.as_object_mut() {\n'
            '                obj.insert("id".to_string(), Value::String(next));\n'
            "            }\n"
            "        }\n"
            "        store.push(record.clone());\n"
            "        record\n"
            "    }\n\n"
            "    pub fn list(&self, entity: &str) -> Vec<Value> {\n"
            "        self.items.get(entity).cloned().unwrap_or_default()\n"
            "    }\n\n"
            "    pub fn get(&self, entity: &str, item_id: &str) -> Option<Value> {\n"
            "        self.items\n"
            "            .get(entity)?\n"
            "            .iter()\n"
            '            .find(|v| v.get("id").and_then(|i| i.as_str()) == Some(item_id))\n'
            "            .cloned()\n"
            "    }\n\n"
            "    pub fn update(&mut self, entity: &str, item_id: &str, payload: Value) -> Option<Value> {\n"
            "        let store = self.items.get_mut(entity)?;\n"
            '        let idx = store.iter().position(|v| {\n'
            '            v.get("id").and_then(|i| i.as_str()) == Some(item_id)\n'
            "        })?;\n"
            "        let mut record = payload;\n"
            '        if let Some(obj) = record.as_object_mut() {\n'
            '            obj.insert("id".to_string(), Value::String(item_id.to_string()));\n'
            "        }\n"
            "        store[idx] = record.clone();\n"
            "        Some(record)\n"
            "    }\n\n"
            "    pub fn delete(&mut self, entity: &str, item_id: &str) -> bool {\n"
            "        match self.items.get_mut(entity) {\n"
            "            Some(store) => {\n"
            "                let before = store.len();\n"
            '                store.retain(|v| v.get("id").and_then(|i| i.as_str()) != Some(item_id));\n'
            "                store.len() != before\n"
            "            }\n"
            "            None => false,\n"
            "        }\n"
            "    }\n"
            "}\n\n"
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    use super::*;\n"
            "    use serde_json::json;\n\n"
            "    #[test]\n"
            "    fn create_assigns_ids_and_round_trips() {\n"
            "        let mut stores = Stores::default();\n"
            '        let created = stores.create("t", json!({"name": "a"}));\n'
            '        assert_eq!(created["id"], json!("1"));\n'
            '        assert!(stores.get("t", "1").is_some());\n'
            '        assert!(stores.delete("t", "1"));\n'
            "        assert!(stores.get(\"t\", \"1\").is_none());\n"
            "    }\n"
            "}\n"
        )

    def _security(self) -> str:
        return (
            "//! API-key authorization (fail-closed when unconfigured).\n"
            "use axum::http::StatusCode;\n\n"
            "pub fn authorize(provided: Option<&str>, expected: &str) -> Result<(), StatusCode> {\n"
            "    if expected.is_empty() {\n"
            "        return Err(StatusCode::SERVICE_UNAVAILABLE);\n"
            "    }\n"
            "    match provided {\n"
            "        Some(value) if constant_time_eq(value.as_bytes(), expected.as_bytes()) => Ok(()),\n"
            "        _ => Err(StatusCode::UNAUTHORIZED),\n"
            "    }\n"
            "}\n\n"
            "fn constant_time_eq(a: &[u8], b: &[u8]) -> bool {\n"
            "    if a.len() != b.len() {\n"
            "        return false;\n"
            "    }\n"
            "    a.iter()\n"
            "        .zip(b.iter())\n"
            "        .fold(0u8, |acc, (x, y)| acc | (x ^ y))\n"
            "        == 0\n"
            "}\n\n"
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    use super::*;\n\n"
            "    #[test]\n"
            "    fn unconfigured_key_refuses_requests() {\n"
            "        assert_eq!(authorize(None, \"\"), Err(StatusCode::SERVICE_UNAVAILABLE));\n"
            "    }\n\n"
            "    #[test]\n"
            "    fn wrong_key_is_unauthorized_and_right_key_passes() {\n"
            "        assert_eq!(authorize(Some(\"wrong\"), \"k\"), Err(StatusCode::UNAUTHORIZED));\n"
            "        assert_eq!(authorize(Some(\"k\"), \"k\"), Ok(()));\n"
            "    }\n"
            "}\n"
        )

    def _behavior_runtime(self) -> str:
        return r'''//! Deterministic runtime for the bounded ISR expression language.
use rust_decimal::Decimal;
use serde_json::Value;
use std::collections::HashMap;
use std::str::FromStr;

fn field_value(path: &str, context: &Value) -> Result<Value, String> {
    if let Some(value) = context.get(path) { return Ok(value.clone()); }
    let mut current = context;
    for part in path.split('.') {
        current = current.get(part).ok_or_else(|| format!("missing expression field: {path}"))?;
    }
    Ok(current.clone())
}

fn decimal(value: &Value) -> Result<Decimal, String> {
    let text = match value {
        Value::Number(number) => number.to_string(),
        Value::String(text) => text.clone(),
        _ => return Err("arithmetic operand is not numeric".to_string()),
    };
    Decimal::from_str(&text).map_err(|_| "arithmetic operand is not numeric".to_string())
}

fn decimal_value(value: Decimal) -> Value {
    Value::String(value.normalize().to_string())
}

pub fn evaluate_expression(expression: &Value, context: &Value) -> Result<Value, String> {
    let op = expression.get("op").and_then(Value::as_str).ok_or("missing expression operator")?;
    let args = expression.get("args").and_then(Value::as_array).cloned().unwrap_or_default();
    if op == "literal" { return expression.get("value").cloned().ok_or("missing literal value".to_string()); }
    if op == "field" {
        let path = expression.get("field_ref").and_then(Value::as_str).ok_or("missing field_ref")?;
        return field_value(path, context);
    }
    if op == "and" {
        let left = evaluate_expression(args.get(0).ok_or("missing left operand")?, context)?;
        if !left.as_bool().unwrap_or(false) { return Ok(Value::Bool(false)); }
        let right = evaluate_expression(args.get(1).ok_or("missing right operand")?, context)?;
        return Ok(Value::Bool(right.as_bool().unwrap_or(false)));
    }
    if op == "or" {
        let left = evaluate_expression(args.get(0).ok_or("missing left operand")?, context)?;
        if left.as_bool().unwrap_or(false) { return Ok(Value::Bool(true)); }
        let right = evaluate_expression(args.get(1).ok_or("missing right operand")?, context)?;
        return Ok(Value::Bool(right.as_bool().unwrap_or(false)));
    }
    if op == "if_else" {
        let condition = evaluate_expression(args.get(0).ok_or("missing condition")?, context)?;
        let branch = if condition.as_bool().unwrap_or(false) { args.get(1) } else { args.get(2) };
        return evaluate_expression(branch.ok_or("missing conditional branch")?, context);
    }
    let values: Result<Vec<Value>, String> = args.iter().map(|arg| evaluate_expression(arg, context)).collect();
    let values = values?;
    match op {
        "add" => Ok(decimal_value(decimal(&values[0])? + decimal(&values[1])?)),
        "subtract" => Ok(decimal_value(decimal(&values[0])? - decimal(&values[1])?)),
        "multiply" => Ok(decimal_value(decimal(&values[0])? * decimal(&values[1])?)),
        "divide" => {
            let divisor = decimal(&values[1])?;
            if divisor == Decimal::ZERO { return Err("division by zero".to_string()); }
            Ok(decimal_value(decimal(&values[0])? / divisor))
        },
        "equal" => Ok(Value::Bool(values[0] == values[1])),
        "not_equal" => Ok(Value::Bool(values[0] != values[1])),
        "less_than" => Ok(Value::Bool(decimal(&values[0])? < decimal(&values[1])?)),
        "less_or_equal" => Ok(Value::Bool(decimal(&values[0])? <= decimal(&values[1])?)),
        "greater_than" => Ok(Value::Bool(decimal(&values[0])? > decimal(&values[1])?)),
        "greater_or_equal" => Ok(Value::Bool(decimal(&values[0])? >= decimal(&values[1])?)),
        "not" => Ok(Value::Bool(!values[0].as_bool().unwrap_or(false))),
        _ => Err(format!("unsupported expression operator: {op}")),
    }
}

pub fn validate_fields(fields: &Value, payload: &Value) -> Result<(), String> {
    let object = payload.as_object().ok_or("record must be an object")?;
    let specs = fields.as_array().ok_or("field schema must be an array")?;
    for key in object.keys() {
        if !specs.iter().any(|spec| spec.get("name").and_then(Value::as_str) == Some(key.as_str())) {
            return Err(format!("unknown field: {key}"));
        }
    }
    for spec in specs {
        let name = spec.get("name").and_then(Value::as_str).ok_or("field name missing")?;
        let value = object.get(name);
        let required = spec.get("required").and_then(Value::as_bool).unwrap_or(true);
        let nullable = spec.get("nullable").and_then(Value::as_bool).unwrap_or(false);
        if value.is_none() {
            if required { return Err(format!("missing required field: {name}")); }
            continue;
        }
        let value = value.unwrap();
        if value.is_null() {
            if !nullable { return Err(format!("field cannot be null: {name}")); }
            continue;
        }
        let kind = spec.get("value_type").and_then(Value::as_str).unwrap_or("");
        let valid = match kind {
            "string" | "identifier" | "date" | "datetime" => value.is_string(),
            "integer" => value.as_i64().is_some(),
            "boolean" => value.is_boolean(),
            "decimal" | "money" => decimal(value).is_ok(),
            _ => false,
        };
        if !valid { return Err(format!("invalid type for field: {name}")); }
        if kind == "decimal" || kind == "money" {
            let amount = decimal(value)?;
            if let Some(scale) = spec.get("scale").and_then(Value::as_u64) {
                if amount.scale() as u64 > scale {
                    return Err(format!("{name} exceeds declared decimal scale"));
                }
            }
            if let Some(precision) = spec.get("precision").and_then(Value::as_u64) {
                let digits = amount.mantissa().unsigned_abs().to_string().len() as u64;
                if digits > precision {
                    return Err(format!("{name} exceeds declared decimal precision"));
                }
            }
        }
        if let Some(constraints) = spec.get("constraints").and_then(Value::as_array) {
            for constraint in constraints {
                let operator = constraint.get("operator").and_then(Value::as_str).unwrap_or("");
                let bound = constraint.get("value").ok_or("constraint value missing")?;
                match operator {
                    "min" => {
                        if decimal(value)? < decimal(bound)? { return Err(format!("{name} is below minimum")); }
                    },
                    "max" => {
                        if decimal(value)? > decimal(bound)? { return Err(format!("{name} is above maximum")); }
                    },
                    "min_length" => {
                        if value.as_str().map(str::len).unwrap_or(0) < bound.as_u64().unwrap_or(0) as usize { return Err(format!("{name} is too short")); }
                    },
                    "max_length" => {
                        if value.as_str().map(str::len).unwrap_or(usize::MAX) > bound.as_u64().unwrap_or(usize::MAX as u64) as usize { return Err(format!("{name} is too long")); }
                    },
                    "one_of" => {
                        if !bound.as_array().map(|choices| choices.contains(value)).unwrap_or(false) { return Err(format!("{name} is not an allowed value")); }
                    },
                    _ => return Err(format!("unsupported field constraint: {operator}")),
                }
            }
        }
    }
    Ok(())
}

pub fn authorize(policies: &Value, role: &str, action: &str, resource: &str, attributes: &Value) -> bool {
    let mut allowed = false;
    for policy in policies.as_array().into_iter().flatten() {
        for rule in policy.get("rules").and_then(Value::as_array).into_iter().flatten() {
            let has_role = rule.get("roles").and_then(Value::as_array).map(|xs| xs.iter().any(|x| x.as_str() == Some(role))).unwrap_or(false);
            let has_action = rule.get("actions").and_then(Value::as_array).map(|xs| xs.iter().any(|x| x.as_str() == Some(action))).unwrap_or(false);
            let target = rule.get("resource").and_then(Value::as_str).unwrap_or("");
            if !has_role || !has_action || (target != resource && target != "*") { continue; }
            let conditions_match = rule.get("conditions").and_then(Value::as_object).map(|conditions| conditions.iter().all(|(key, expected)| attributes.get(key) == Some(expected))).unwrap_or(true);
            if !conditions_match { continue; }
            match rule.get("effect").and_then(Value::as_str) {
                Some("deny") => return false,
                Some("allow") => allowed = true,
                _ => {},
            }
        }
    }
    allowed
}

pub fn apply_effect<F>(effect: &Value, key: Option<&str>, execute: F, ledger: &mut HashMap<String, Value>) -> Result<Value, String>
where
    F: FnOnce() -> Result<Value, String>,
{
    let idempotent = effect.get("idempotent").and_then(Value::as_bool).unwrap_or(false);
    let key_required = effect.get("idempotency_key_required").and_then(Value::as_bool).unwrap_or(false);
    if key_required && key.is_none() { return Err("idempotency key required".to_string()); }
    if idempotent {
        let key = key.ok_or("idempotent effect requires a key")?;
        let effect_kind = effect.get("effect_kind").and_then(Value::as_str).unwrap_or("effect");
        let identity = format!("{effect_kind}:{key}");
        if let Some(previous) = ledger.get(&identity) { return Ok(previous.clone()); }
        let result = execute()?;
        ledger.insert(identity, result.clone());
        return Ok(result);
    }
    if key.is_some() {
        return Err("non-idempotent effect cannot claim keyed deduplication".to_string());
    }
    execute()
}

pub fn apply_transition(transitions: &Value, transition_id: &str, current_state: &str, context: &Value) -> Result<String, String> {
    let transition = transitions.as_array().and_then(|items| items.iter().find(|item| item.get("transition_id").and_then(Value::as_str) == Some(transition_id))).ok_or("unknown transition")?;
    if transition.get("source_state").and_then(Value::as_str) != Some(current_state) { return Err("transition source state mismatch".to_string()); }
    if let Some(guard) = transition.get("guard") {
        if !evaluate_expression(guard, context)?.as_bool().unwrap_or(false) { return Err("transition guard rejected".to_string()); }
    }
    transition.get("target_state").and_then(Value::as_str).map(str::to_string).ok_or("target state missing".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn decimal_expression_uses_exact_decimal_arithmetic() {
        let expression = json!({"op":"multiply","args":[{"op":"field","field_ref":"hours"},{"op":"field","field_ref":"rate"}]});
        assert_eq!(evaluate_expression(&expression, &json!({"hours":7,"rate":"12.50"})).unwrap(), json!("87.5"));
    }

    #[test]
    fn validation_rejects_unknown_and_invalid_fields() {
        let fields = json!([{"name":"amount","value_type":"money","required":true,"nullable":false,"constraints":[{"operator":"min","value":0}]}]);
        assert!(validate_fields(&fields, &json!({"amount":"10.00"})).is_ok());
        assert!(validate_fields(&fields, &json!({"amount":"-1"})).is_err());
        assert!(validate_fields(&fields, &json!({"amount":"10","other":1})).is_err());
    }

    #[test]
    fn money_precision_and_scale_are_enforced() {
        let fields = json!([{"name":"amount","value_type":"money","required":true,"nullable":false,"precision":5,"scale":2}]);
        assert!(validate_fields(&fields, &json!({"amount":"999.99"})).is_ok());
        assert!(validate_fields(&fields, &json!({"amount":"1000.00"})).is_err());
        assert!(validate_fields(&fields, &json!({"amount":"1.234"})).is_err());
    }

    #[test]
    fn authorization_is_default_deny_and_explicit_deny_wins() {
        let policies = json!([{"rules":[{"effect":"allow","roles":["approver"],"actions":["payroll.approve"],"resource":"PayrollRun","conditions":{}},{"effect":"deny","roles":["approver"],"actions":["payroll.approve"],"resource":"PayrollRun","conditions":{}}]}]);
        assert!(!authorize(&json!([]), "approver", "payroll.approve", "PayrollRun", &json!({})));
        assert!(!authorize(&policies, "approver", "payroll.approve", "PayrollRun", &json!({})));
    }

    #[test]
    fn effect_idempotency_returns_prior_result() {
        let effect = json!({"effect_kind":"bank_transfer","idempotent":true,"idempotency_key_required":true});
        let mut ledger = HashMap::new();
        let mut calls = 0;
        let first = apply_effect(&effect, Some("run-1"), || { calls += 1; Ok(json!({"status":"queued"})) }, &mut ledger).unwrap();
        let retry = apply_effect(&effect, Some("run-1"), || { calls += 1; Ok(json!({"status":"duplicate"})) }, &mut ledger).unwrap();
        assert_eq!(first, json!({"status":"queued"}));
        assert_eq!(retry, first);
        assert_eq!(calls, 1);
        assert!(apply_effect(&effect, None, || Ok(json!({})), &mut ledger).is_err());
    }

    #[test]
    fn transition_guard_is_enforced() {
        let transitions = json!([{"transition_id":"submit","source_state":"draft","target_state":"submitted","guard":{"op":"greater_than","args":[{"op":"field","field_ref":"gross"},{"op":"literal","value":0}]}}]);
        assert_eq!(apply_transition(&transitions, "submit", "draft", &json!({"gross":100})).unwrap(), "submitted");
        assert!(apply_transition(&transitions, "submit", "draft", &json!({"gross":0})).is_err());
    }
}
'''

    def _effect(self, path: str, plan: CompilationPlan) -> str:
        stem = path.rsplit("/", 1)[-1][: -len(".rs")]
        effect = next((item for item in plan.effects if _slug(item.name) == stem), None)
        if effect is None or effect.behavior is None:
            return "//! Effect contract unavailable; this module is not executable.\n"
        spec_json = json.dumps(effect.behavior.model_dump(mode="json"))
        spec_literal = json.dumps(spec_json)
        lines = [
            "//! Generated effect adapter with explicit executor and idempotency contract.",
            "use serde_json::Value;",
            "use std::collections::HashMap;",
            "",
            f"const EFFECT_JSON: &str = {spec_literal};",
            "",
            "pub fn apply<F>(idempotency_key: Option<&str>, ledger: &mut HashMap<String, Value>, executor: F) -> Result<Value, String>",
            "where",
            "    F: FnOnce() -> Result<Value, String>,",
            "{",
            "    let effect: Value = serde_json::from_str(EFFECT_JSON).map_err(|e| e.to_string())?;",
            "    crate::core::behavior::apply_effect(&effect, idempotency_key, executor, ledger)",
            "}",
        ]
        if effect.behavior.idempotent:
            lines += [
                "",
                "#[cfg(test)]",
                "mod tests {",
                "    use super::*;",
                "    use serde_json::json;",
                "",
                "    #[test]",
                "    fn retries_return_the_original_result_without_reexecuting_handler() {",
                "        let mut ledger = HashMap::new();",
                "        let mut calls = 0;",
                '        let first = apply(Some("same-key"), &mut ledger, || { calls += 1; Ok(json!({"status":"queued"})) }).unwrap();',
                '        let retry = apply(Some("same-key"), &mut ledger, || { calls += 1; Ok(json!({"status":"duplicate"})) }).unwrap();',
                "        assert_eq!(first, retry);",
                "        assert_eq!(calls, 1);",
                "    }",
            ]
            if effect.behavior.idempotency_key_required:
                lines += [
                    "",
                    "    #[test]",
                    "    fn required_key_is_enforced() {",
                    "        let mut ledger = HashMap::new();",
                    "        assert!(apply(None, &mut ledger, || Ok(json!({}))).is_err());",
                    "    }",
                ]
            lines.append("}")
        return "\n".join(lines) + "\n"

    def _domain(self, path: str, plan: CompilationPlan) -> str:
        stem = path.rsplit("/", 1)[-1][: -len(".rs")]
        entities = plan_entities(plan)
        entity = next((e for e in entities if e["mod"] == stem), None)
        cls = entity["cls"] if entity else _cls(stem)
        model = next((item for item in plan.data_models if _slug(item.entity_name) == stem), None)
        if model is None or model.behavior is None:
            return (
                f"//! Domain model {cls} (generated).\n"
                "#[derive(Debug, Default, serde::Serialize, serde::Deserialize)]\n"
                "#[serde(default)]\n"
                f"pub struct {cls} {{\n"
                "    pub id: Option<String>,\n"
                "    pub name: String,\n"
                "}\n"
            )
        type_names = {
            "string": "String", "identifier": "String", "date": "String", "datetime": "String",
            "integer": "i64", "decimal": "rust_decimal::Decimal", "money": "rust_decimal::Decimal",
            "boolean": "bool",
        }
        lines = [
            f"//! Typed domain model {cls} (generated from ISR).",
            "#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]",
            f"pub struct {cls} {{",
        ]
        for field in model.behavior.fields:
            annotation = type_names[field.value_type.value]
            optional = field.nullable or not field.required
            if optional:
                annotation = f"Option<{annotation}>"
                lines.append("    #[serde(default)]")
            lines.append(f"    pub {field.name}: {annotation},")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def _application(self, path: str, plan: CompilationPlan) -> str:
        stem = path.rsplit("/", 1)[-1][: -len(".rs")]
        svc = next((s for s in plan_services(plan) if s["mod"] == stem), None)
        service = next((item for item in plan.services if _slug(item.name) == stem), None)
        name = svc["name"] if svc else stem
        owned = svc["owned"] if svc else []
        lines = [
            f"//! Application behavior for service {name} (generated from ISR).",
            "use serde_json::Value;",
            "",
            "pub fn service_name() -> &'static str {",
            f'    "{name}"',
            "}",
            "",
        ]
        for mod_e in owned:
            fn = mod_e.lower()
            model = next((item for item in plan.data_models if _slug(item.entity_name) == mod_e), None)
            if model is not None and model.behavior is not None:
                schema_json = json.dumps([field.model_dump(mode="json") for field in model.behavior.fields])
                schema_literal = json.dumps(schema_json)
                lines += [
                    f"pub fn validate_{fn}(payload: &Value) -> Result<(), String> {{",
                    f"    let fields: Value = serde_json::from_str({schema_literal}).map_err(|e| e.to_string())?;",
                    "    crate::core::behavior::validate_fields(&fields, payload)",
                    "}",
                    "",
                ]
            else:
                lines += [
                    f"pub fn validate_{fn}(payload: &Value) -> Result<(), String> {{",
                    '    let name = payload.get("name").and_then(|v| v.as_str()).unwrap_or("");',
                    '    if name.is_empty() { return Err("name must be a non-empty string".to_string()); }',
                    "    Ok(())",
                    "}",
                    "",
                ]
        if service is not None and service.behavior is not None:
            rules = [item.model_dump(mode="json") for item in service.behavior.rules]
            transitions = [item.model_dump(mode="json") for item in service.behavior.transitions]
            rules_literal = json.dumps(json.dumps(rules))
            transitions_literal = json.dumps(json.dumps(transitions))
            lines += [
                f"pub fn evaluate_rule(rule_id: &str, context: &Value) -> Result<Value, String> {{",
                f"    let rules: Value = serde_json::from_str({rules_literal}).map_err(|e| e.to_string())?;",
                "    let rule = rules.as_array().and_then(|items| items.iter().find(|item| item.get(\"rule_id\").and_then(Value::as_str) == Some(rule_id))).ok_or(\"unknown business rule\")?;",
                "    crate::core::behavior::evaluate_expression(&rule[\"expression\"], context)",
                "}",
                "",
                "pub fn apply_transition(transition_id: &str, current_state: &str, context: &Value) -> Result<String, String> {",
                f"    let transitions: Value = serde_json::from_str({transitions_literal}).map_err(|e| e.to_string())?;",
                "    crate::core::behavior::apply_transition(&transitions, transition_id, current_state, context)",
                "}",
                "",
            ]
        if service is not None and service.security_policies:
            policies = [policy.behavior.model_dump(mode="json") if policy.behavior is not None else {"rules": []} for policy in service.security_policies]
            policies_literal = json.dumps(json.dumps(policies))
            lines += [
                "pub fn authorize(role: &str, action: &str, resource: &str, attributes: &Value) -> bool {",
                f"    let policies: Value = serde_json::from_str({policies_literal}).expect(\"validated ISR security policy\");",
                "    crate::core::behavior::authorize(&policies, role, action, resource, attributes)",
                "}",
                "",
            ]
        return "\n".join(lines) + "\n"

    def _event(self, path: str, plan: CompilationPlan) -> str:
        stem = path.rsplit("/", 1)[-1][: -len(".rs")]
        ev = next((e for e in plan_events(plan) if e["mod"] == stem), None)
        name = ev["name"] if ev else stem
        fn = stem.lower()
        return (
            f"//! Event handler for {name} (generated, validated).\n"
            "use serde_json::Value;\n"
            "\n"
            f"pub fn handle_{fn}(payload: Value) -> Result<Value, &'static str> {{\n"
            "    if !payload.is_object() {\n"
            '        return Err("event payload must be an object");\n'
            "    }\n"
            '    let envelope = serde_json::json!({\n'
            f'        "type": "{name}",\n'
            '        "payload": payload,\n'
            "    });\n"
            "    Ok(envelope)\n"
            "}\n"
            "\n"
            "#[cfg(test)]\n"
            "mod tests {\n"
            "    use super::*;\n"
            "    use serde_json::json;\n"
            "\n"
            "    #[test]\n"
            f"    fn {fn}_validates_and_wraps() {{\n"
            '        let out = handle_'
            f"{fn}(json!({{\"k\": 1}})).expect(\"valid payload\");\n"
            f'        assert_eq!(out["type"], json!("{name}"));\n'
            f'        assert!(handle_{fn}(json!([1, 2])).is_err());\n'
            "    }\n"
            "}\n"
        )

    def _main(self, plan: CompilationPlan) -> str:
        entities = plan_entities(plan)
        services = plan_services(plan)
        events = plan_events(plan)
        secured = self._secured(plan)

        l: list[str] = []
        l.append("//! Generated Axum application — wired CRUD, health, OpenAPI.")
        if secured:
            l += [
                "use axum::extract::{Path, Request, State};",
                "use axum::http::{header, HeaderMap, StatusCode};",
                "use axum::middleware::{self, Next};",
                "use axum::response::{IntoResponse, Response};",
                "use axum::routing::get;",
                "use axum::{Json, Router};",
            ]
        else:
            l += [
                "use axum::extract::{Path, State};",
                "use axum::http::{header, StatusCode};",
                "use axum::response::IntoResponse;",
                "use axum::routing::get;",
                "use axum::{Json, Router};",
            ]
        if events:
            l.append("use axum::routing::post;")
        l += [
            "use serde_json::{json, Value};",
            "use std::sync::{Arc, Mutex};",
            "",
            "pub mod application;",
            "pub mod domain;",
            "pub mod events;",
            "pub mod infrastructure;",
            "pub mod effects;"
        ]
        l.append("pub mod core;")
        l.append("")
        l += [
            "use infrastructure::repositories::Stores;",
        ]
        for e in entities:
            l.append(f"use domain::{e['mod']}::{e['cls']};")
        l += [
            "",
            "",
            "#[derive(Clone)]",
            "pub struct AppState {",
            "    pub stores: Arc<Mutex<Stores>>,",
            "    pub api_key: String,",
            "}",
            "",
            "",
            "pub fn new_state() -> AppState {",
            "    AppState {",
            "        stores: Arc::new(Mutex::new(Stores::default())),",
            '        api_key: std::env::var("GENERATED_API_KEY").unwrap_or_default(),',
            "    }",
            "}",
            "",
            "",
            'async fn health() -> &\'static str {',
            '    "ok"',
            "}",
            "",
            "",
            "async fn openapi_spec() -> impl IntoResponse {",
            '    ([(header::CONTENT_TYPE, "application/json")], include_str!("../openapi.json"))',
            "}",
            "",
        ]

        if secured:
            l += [
                "fn check_auth(state: &AppState, headers: &HeaderMap) -> Result<(), StatusCode> {",
                "    let provided = headers",
                '        .get("x-api-key")',
                "        .and_then(|v| v.to_str().ok());",
                "    core::security::authorize(provided, &state.api_key)",
                "}",
                "",
                "",
                "async fn auth_mw(",
                "    State(state): State<AppState>,",
                "    req: Request,",
                "    next: Next,",
                ") -> Result<Response, StatusCode> {",
                "    check_auth(&state, req.headers())?;",
                "    Ok(next.run(req).await)",
                "}",
                "",
                "",
            ]

        # service singletons via application modules (name always wired)
        l.append("fn service_catalog() -> Vec<Value> {")
        if services:
            l.append("    vec![")
            for s in services:
                owned = json.dumps([m for m in s["owned"]])
                l.append(
                    f'        json!({{"service": application::{s["mod"]}::service_name(), '
                    f'"entities": {owned}}}),'
                )
            l.append("    ]")
        else:
            l.append("    vec![]")
        l += ["}", "", ""]

        # handlers
        for e in entities:
            fn = e["mod"].lower()
            l += [
                f"async fn list_{_plural(fn)}(State(state): State<AppState>) -> Json<Vec<Value>> {{",
                f'    let stores = state.stores.lock().expect("store lock");',
                f'    Json(stores.list("{e["mod"]}"))',
                "}",
                "",
                f"async fn create_{fn}(",
                "    State(state): State<AppState>,",
                "    Json(payload): Json<Value>,",
                ") -> Result<(StatusCode, Json<Value>), StatusCode> {",
                f"    application::{e['service_mod']}::validate_{fn}(&payload)",
                "        .map_err(|_| StatusCode::UNPROCESSABLE_ENTITY)?;",
                f"    let record: {e['cls']} = serde_json::from_value(payload)",
                "        .map_err(|_| StatusCode::UNPROCESSABLE_ENTITY)?;",
                "    let value = serde_json::to_value(&record)",
                "        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;",
                f'    let mut stores = state.stores.lock().expect("store lock");',
                f'    let created = stores.create("{e["mod"]}", value);',
                "    Ok((StatusCode::CREATED, Json(created)))",
                "}",
                "",
                f"async fn get_{fn}(",
                "    State(state): State<AppState>,",
                "    Path(item_id): Path<String>,",
                ") -> Result<Json<Value>, StatusCode> {",
                f'    let stores = state.stores.lock().expect("store lock");',
                f'    stores.get("{e["mod"]}", &item_id)',
                "        .map(Json)",
                '        .ok_or(StatusCode::NOT_FOUND)',
                "}",
                "",
                f"async fn update_{fn}(",
                "    State(state): State<AppState>,",
                "    Path(item_id): Path<String>,",
                "    Json(payload): Json<Value>,",
                ") -> Result<Json<Value>, StatusCode> {",
                f"    application::{e['service_mod']}::validate_{fn}(&payload)",
                "        .map_err(|_| StatusCode::UNPROCESSABLE_ENTITY)?;",
                f"    let record: {e['cls']} = serde_json::from_value(payload)",
                "        .map_err(|_| StatusCode::UNPROCESSABLE_ENTITY)?;",
                "    let value = serde_json::to_value(&record)",
                "        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;",
                f'    let mut stores = state.stores.lock().expect("store lock");',
                f'    stores.update("{e["mod"]}", &item_id, value)',
                "        .map(Json)",
                '        .ok_or(StatusCode::NOT_FOUND)',
                "}",
                "",
                f"async fn delete_{fn}(",
                "    State(state): State<AppState>,",
                "    Path(item_id): Path<String>,",
                ") -> Result<StatusCode, StatusCode> {",
                f'    let mut stores = state.stores.lock().expect("store lock");',
                f'    if stores.delete("{e["mod"]}", &item_id) {{',
                "        Ok(StatusCode::NO_CONTENT)",
                "    } else {",
                "        Err(StatusCode::NOT_FOUND)",
                "    }",
                "}",
                "",
            ]

        l += [
            "async fn list_services() -> Json<Vec<Value>> {",
            "    Json(service_catalog())",
            "}",
            "",
        ]
        for ev in events:
            fn = ev["mod"].lower()
            l += [
                f"async fn ingest_{fn}(Json(payload): Json<Value>) -> Result<Json<Value>, StatusCode> {{",
                f"    events::{ev['mod']}::handle_{fn}(payload)",
                "        .map(Json)",
                "        .map_err(|_| StatusCode::UNPROCESSABLE_ENTITY)",
                "}",
                "",
            ]
        if events:
            l += [
                "async fn list_events() -> Json<Vec<&'static str>> {",
                f"    Json(vec![{', '.join(json.dumps(e['name']) for e in events)}])",
                "}",
                "",
            ]

        # router assembly
        l += [
            "pub fn build_app(state: AppState) -> Router {",
            f"    let {'mut business' if secured else 'business'} = Router::new()",
        ]
        for e in entities:
            fn = e["mod"].lower()
            l.append(
                f'        .route("/api/{_plural(e["mod"])}", '
                f"get(list_{_plural(fn)}).post(create_{fn}))"
            )
            l.append(
                f'        .route("/api/{_plural(e["mod"])}/{{item_id}}", '
                f"get(get_{fn}).put(update_{fn}).delete(delete_{fn}))"
            )
        l.append('        .route("/api/services", get(list_services))')
        if events:
            for ev in events:
                fn = ev["mod"].lower()
                l.append(
                    f'        .route("/api/events/{ev["mod"]}", post(ingest_{fn}))'
                )
            l.append('        .route("/api/events", get(list_events))')
        l.append("        .with_state(state.clone());")
        if secured:
            l += [
                "    business = business.layer(middleware::from_fn_with_state(state, auth_mw));",
            ]
        l += [
            "    Router::new()",
            '        .route("/health", get(health))',
            '        .route("/openapi.json", get(openapi_spec))',
            "        .merge(business)",
            "}",
            "",
            "",
            "#[tokio::main]",
            "async fn main() {",
            "    let state = new_state();",
            "    let app = build_app(state);",
            '    let listener = tokio::net::TcpListener::bind("0.0.0.0:8000")',
            '        .await',
            '        .expect("bind 0.0.0.0:8000");',
            '    axum::serve(listener, app).await.expect("server exited");',
            "}",
        ]

        # tests
        l += [
            "",
            "#[cfg(test)]",
            "mod tests {",
            "    use super::*;",
            "    use serde_json::json;",
            "",
            "    #[test]",
            "    fn state_initialises_empty_store() {",
            "        let state = new_state();",
            '        assert!(state.stores.lock().expect("lock").list("orders").is_empty());',
            "    }",
            "",
            "    #[tokio::test]",
            "    async fn health_serves_ok() {",
            '        assert_eq!(health().await, "ok");',
            "    }",
            "",
        ]
        if entities:
            e = entities[0]
            fn = e["mod"].lower()
            plural = _plural(fn)
            model = next((item for item in plan.data_models if _slug(item.entity_name) == e["mod"]), None)
            if model is not None and model.behavior is not None:
                payload = {}
                updated_payload = {}
                for field in model.behavior.fields:
                    kind = field.value_type.value
                    if kind == "integer":
                        value, updated = 1, 2
                    elif kind in ("decimal", "money"):
                        value, updated = "10.00", "20.00"
                    elif kind == "boolean":
                        value, updated = True, False
                    elif kind == "date":
                        value, updated = "2026-01-01", "2026-01-02"
                    elif kind == "datetime":
                        value, updated = "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
                    elif kind == "identifier":
                        value, updated = f"{field.name}-alpha", f"{field.name}-beta"
                    else:
                        value, updated = "alpha", "beta"
                    payload[field.name] = value
                    updated_payload[field.name] = updated
                tested_field = model.behavior.fields[0].name
            else:
                payload = {"name": "alpha"}
                updated_payload = {"name": "beta"}
                tested_field = "name"
            payload_json = json.dumps(payload, sort_keys=True)
            updated_json = json.dumps(updated_payload, sort_keys=True)
            expected_created = json.dumps(payload[tested_field])
            expected_updated = json.dumps(updated_payload[tested_field])
            l += [
                "    #[tokio::test]",
                f"    async fn crud_roundtrip_{plural}() {{",
                "        let state = new_state();",
                f"        let created = create_{fn}(State(state.clone()), Json(json!({payload_json})))",
                '            .await',
                '            .expect("create");',
                "        assert_eq!(created.0, StatusCode::CREATED);",
                f'        assert_eq!(created.1.0[{json.dumps(tested_field)}], json!({expected_created}));',
                f'        let item_id = created.1.0["id"].as_str().expect("id").to_string();',
                f"        let listed = list_{plural}(State(state.clone())).await;",
                "        assert_eq!(listed.0.len(), 1);",
                f"        let fetched = get_{fn}(State(state.clone()), Path(item_id.clone()))",
                '            .await',
                '            .expect("get");',
                f'        assert_eq!(fetched.0[{json.dumps(tested_field)}], json!({expected_created}));',
                f"        let updated = update_{fn}(",
                "            State(state.clone()),",
                "            Path(item_id.clone()),",
                f"            Json(json!({updated_json})),",
                "        )",
                "        .await",
                '        .expect("update");',
                f'        assert_eq!(updated.0[{json.dumps(tested_field)}], json!({expected_updated}));',
                f"        let deleted = delete_{fn}(State(state.clone()), Path(item_id))",
                '            .await',
                '            .expect("delete");',
                "        assert_eq!(deleted, StatusCode::NO_CONTENT);",
                f'        let gone = get_{fn}(State(state), Path("missing".to_string())).await;',
                "        assert!(gone.is_err());",
                "    }",
                "",
            ]
        if secured:
            l += [
                "    #[test]",
                "    fn auth_refuses_unconfigured_and_wrong_keys() {",
                "        let mut state = new_state();",
                '        state.api_key = String::new();',
                "        let headers = HeaderMap::new();",
                "        assert_eq!(",
                "            check_auth(&state, &headers),",
                "            Err(StatusCode::SERVICE_UNAVAILABLE)",
                "        );",
                '        state.api_key = "k".to_string();',
                "        assert_eq!(check_auth(&state, &headers), Err(StatusCode::UNAUTHORIZED));",
                "        let mut headers = HeaderMap::new();",
                "        headers.insert(",
                '            "x-api-key",',
                '            axum::http::HeaderValue::from_static("k"),',
                "        );",
                "        assert_eq!(check_auth(&state, &headers), Ok(()));",
                "    }",
                "",
            ]
        if events:
            ev = events[0]
            fn = ev["mod"].lower()
            l += [
                "    #[test]",
                f"    fn event_ingest_validates_payload() {{",
                f'        let out = events::{ev["mod"]}::handle_{fn}(json!({{"k": 1}}))',
                '            .expect("valid");',
                f'        assert_eq!(out["type"], json!("{ev["name"]}"));',
                f'        assert!(events::{ev["mod"]}::handle_{fn}(json!([1])).is_err());',
                "    }",
                "",
            ]
        l.append("}")
        return "\n".join(l) + "\n"

    def _openapi(self, plan: CompilationPlan) -> str:
        entities = plan_entities(plan)
        events = plan_events(plan)
        secured = self._secured(plan)

        def op(summary: str, code: str) -> dict:
            o: dict = {
                "summary": summary,
                "responses": {code: {"description": summary}},
            }
            if secured:
                o["security"] = [{"ApiKeyAuth": []}]
            return o

        spec: dict = {
            "openapi": "3.1.0",
            "info": {
                "title": plan.isr_id or "generated-service",
                "version": "1.0.0",
            },
            "paths": {
                "/health": {"get": op("Liveness probe", "200")},
                "/api/services": {"get": op("Service catalog", "200")},
            },
        }
        for e in entities:
            base = f"/api/{_plural(e['mod'])}"
            spec["paths"][base] = {
                "get": op(f"List {e['entity']}", "200"),
                "post": op(f"Create {e['entity']}", "201"),
            }
            spec["paths"][f"{base}/{{item_id}}"] = {
                "get": op(f"Get {e['entity']}", "200"),
                "put": op(f"Update {e['entity']}", "200"),
                "delete": op(f"Delete {e['entity']}", "204"),
            }
        if events:
            spec["paths"]["/api/events"] = {"get": op("List events", "200")}
            for ev in events:
                spec["paths"][f"/api/events/{ev['mod']}"] = {
                    "post": op(f"Ingest {ev['name']}", "200"),
                }
        if secured:
            spec["components"] = {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-Key",
                    }
                }
            }
        return json.dumps(spec, indent=2) + "\n"

    def _k8s(self) -> str:
        return (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: generated-axum\n"
            "  labels:\n"
            "    app: generated-axum\n"
            "spec:\n"
            "  replicas: 1\n"
            "  selector:\n"
            "    matchLabels:\n"
            "      app: generated-axum\n"
            "  template:\n"
            "    metadata:\n"
            "      labels:\n"
            "        app: generated-axum\n"
            "    spec:\n"
            "      containers:\n"
            "        - name: app\n"
            "          image: generated-axum:latest\n"
            "          ports:\n"
            "            - containerPort: 8000\n"
            "          env:\n"
            "            - name: GENERATED_API_KEY\n"
            "              value: generated-dev-key\n"
            "          readinessProbe:\n"
            "            httpGet:\n"
            "              path: /health\n"
            "              port: 8000\n"
            "            initialDelaySeconds: 3\n"
            "            periodSeconds: 5\n"
            "---\n"
            "apiVersion: v1\n"
            "kind: Service\n"
            "metadata:\n"
            "  name: generated-axum\n"
            "spec:\n"
            "  selector:\n"
            "    app: generated-axum\n"
            "  ports:\n"
            "    - port: 80\n"
            "      targetPort: 8000\n"
        )

    def _ci(self) -> str:
        return (
            "name: ci\n"
            "on: [push, pull_request]\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: dtolnay/rust-toolchain@stable\n"
            "      - run: cargo test\n"
            "      - run: cargo build --release\n"
        )

    def _readme(self, plan: CompilationPlan) -> str:
        entities = plan_entities(plan)
        services = plan_services(plan)
        events = plan_events(plan)
        secured = self._secured(plan)
        lines = [f"# {plan.isr_id or 'generated-service'}", ""]
        lines.append("Generated Rust/Axum service produced from the ISR compilation plan.")
        lines.append("")
        lines.append("## Services")
        for s in services:
            owned = ", ".join(s["owned"]) or "(no data models)"
            lines.append(f"- `{s['name']}` — entities: {owned}")
        if not services:
            lines.append("- (plan contains no services)")
        lines.append("")
        lines.append("## HTTP surface")
        lines.append("- `GET /health` — liveness")
        lines.append("- `GET /openapi.json` — OpenAPI document")
        lines.append("- `GET /api/services` — service catalog")
        for e in entities:
            lines.append(
                f"- `/api/{_plural(e['mod'])}` — CRUD for `{e['entity']}` "
                "(GET, POST, GET/PUT/DELETE by item_id)"
            )
        if not entities:
            lines.append("- (plan contains no data models)")
        if events:
            lines.append("")
            lines.append("## Events")
            for ev in events:
                lines.append(f"- `{ev['name']}` — `POST /api/events/{ev['mod']}`")
        lines.append("")
        lines.append("## Run")
        lines.append("```bash")
        lines.append("cargo run --release")
        lines.append("```")
        lines.append("Listens on `0.0.0.0:8000`.")
        if secured:
            lines.append("")
            lines.append("Authorization: set `GENERATED_API_KEY` and send `X-API-Key` on every")
            lines.append("business request. Missing configuration refuses requests (fail-closed).")
        lines.append("")
        lines.append("## Test")
        lines.append("```bash")
        lines.append("cargo test")
        lines.append("```")
        lines.append("Tests run in the Dockerfile build stage as well.")
        lines.append("")
        return "\n".join(lines)

    def _docs(self, plan: CompilationPlan) -> str:
        entities = plan_entities(plan)
        services = plan_services(plan)
        events = plan_events(plan)
        lines = [f"# Architecture — {plan.isr_id or 'generated-service'}", ""]
        lines.append("Derived deterministically from the ISR compilation plan.")
        lines.append("")
        lines.append("## Modules")
        lines.append("- `src/main.rs` — app wiring, handlers, router, tests")
        lines.append("- `src/application/` — application validation (use-case rules)")
        lines.append("- `src/domain/` — typed domain models (serde)")
        lines.append("- `src/infrastructure/` — in-memory store (CRUD semantics)")
        lines.append("- `src/events/` — validated event handlers + tests")
        if self._secured(plan):
            lines.append("- `src/core/security.rs` — API-key authorization (fail-closed)")
        lines.append("")
        lines.append("## Services and persisted entities")
        for s in services:
            lines.append(f"- `{s['name']}` persists {s['owned'] or 'nothing'}")
        if not services:
            lines.append("- (plan contains no services)")
        lines.append("")
        lines.append("## Request flow")
        lines.append("1. Router resolves the endpoint under `/api/...`.")
        if self._secured(plan):
            lines.append("2. `auth_mw` admits or rejects the caller (401/503).")
            start = 3
        else:
            start = 2
        lines.append(f"{start}. Application validation rejects malformed payloads (422).")
        lines.append(f"{start + 1}. The store persists the record; serde serializes the response.")
        lines.append("")
        lines.append("## Verification")
        lines.append("Module wiring (`mod.rs`) ensures cargo compiles every emitted file;")
        lines.append("the Dockerfile build stage runs `cargo test` before the release build.")
        if events:
            lines.append("")
            lines.append("## Domain events")
            for ev in events:
                lines.append(f"- `{ev['name']}` validated by `handle_{ev['mod'].lower()}`")
        lines.append("")
        return "\n".join(lines)
