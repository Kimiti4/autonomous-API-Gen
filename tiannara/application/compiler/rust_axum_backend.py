"""Typed Rust/Axum compiler backend.

Consumes only the technology-neutral SystemModel and emits an independently
structured Rust service. It deliberately does not consume Python/Go artifacts.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.application.compiler.writer import write_bundle
from tiannara.domain.models.backend_declaration import ArtifactKind, BackendCapabilityDeclaration
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.capability_manifest import BundleCapability, CapabilityManifest
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.models.genome import Genome
from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.domain.models.system_model import AbstractFieldType, FieldSpec, SystemModel
from .naming import pascal_case, slugify, snake_case

_TYPES = {
    AbstractFieldType.IDENTIFIER: "String", AbstractFieldType.TEXT: "String",
    AbstractFieldType.INTEGER: "i64", AbstractFieldType.DECIMAL: "f64",
    AbstractFieldType.BOOLEAN: "bool", AbstractFieldType.TIMESTAMP: "String",
    AbstractFieldType.ENUMERATION: "String", AbstractFieldType.REFERENCE: "String",
    AbstractFieldType.BINARY: "Vec<u8>", AbstractFieldType.DOCUMENT: "serde_json::Value",
}

class RustAxumBackend:
    backend_id = "rust_axum"

    @property
    def name(self) -> str:
        return self.backend_id

    def build_profile(self, system_name: str) -> BackendBuildProfile:
        return BackendBuildProfile(
            language="rust",
            required_files=("Cargo.toml", "src/main.rs", "src/domain/models.rs", "Dockerfile"),
            verifier_kind="rust",
            build_command=["cargo", "build"],
            test_command=["cargo", "test"],
            runtime_image="rust:1.85-slim",
            requires_build_phase=True,
        )

    def build_profile_declaration(self) -> BackendCapabilityDeclaration:
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=list(self._manifest().capabilities),
            quality_profile=0.80,
            metadata={"language": "rust", "framework": "axum", "style": "typed-hexagonal"},
        )

    def _system_model(self, isr: IntermediateSoftwareRepresentation) -> SystemModel:
        typed = isr.system_model()
        if typed is not None:
            return typed
        raise ValueError("RustAxumBackend requires a typed SystemModel ISR payload")

    def compile(self, isr: IntermediateSoftwareRepresentation, genome: Genome, output_dir: str) -> SystemDeploymentBundle:
        result = self.generate(self._system_model(isr))
        write_bundle(result, output_dir)
        return SystemDeploymentBundle(
            project_id=isr.system_id, backend_name=self.name,
            isr_hash=isr.content_hash(), path=Path(output_dir),
            artifacts=result.file_paths(), capability_manifest=result.capability_manifest,
        )

    def generate(self, system_model: SystemModel) -> CompilationResult:
        slug = slugify(system_model.system_name)
        files = {
            "Cargo.toml": self._cargo(slug),
            "src/main.rs": self._main(slug),
            "src/lib.rs": self._lib(),
            "src/domain/models.rs": self._models(system_model),
            "src/domain/mod.rs": "pub mod models;\n",
            "tests/health.rs": self._test(slug),
            "Dockerfile": self._dockerfile(slug),
            "README.md": f"# {system_model.system_name}\\n\\nGenerated from the technology-neutral ISR.\\n",
        }
        return CompilationResult(
            backend_id=self.backend_id, system_name=slug, files=files,
            capability_manifest=self._manifest(),
        )

    def _cargo(self, slug):
        return f"""[package]
name = "{slug}"
version = "0.1.0"
edition = "2021"

[dependencies]
axum = "0.7"
tokio = {{ version = "1", features = ["macros", "rt-multi-thread", "net"] }}
serde = {{ version = "1", features = ["derive"] }}
serde_json = "1"

[dev-dependencies]
tower = {{ version = "0.5", features = ["util"] }}
"""

    def _models(self, model):
        out = ["use serde::{Deserialize, Serialize};", ""]
        if not model.data_models:
            return "\n".join(out + ["#[derive(Clone, Debug, Serialize, Deserialize)]", "pub struct Item {", "    pub id: String,", "}", ""])
        rust_keywords = {
            "as", "break", "const", "continue", "crate", "else", "enum", "extern",
            "false", "fn", "for", "if", "impl", "in", "let", "loop", "match",
            "mod", "move", "mut", "pub", "ref", "return", "self", "Self", "static",
            "struct", "super", "trait", "true", "type", "unsafe", "use", "where",
            "while", "async", "await", "dyn", "abstract", "become", "box", "do",
            "final", "macro", "override", "priv", "typeof", "unsized", "virtual", "yield",
        }
        for dm in model.data_models:
            out += ["#[derive(Clone, Debug, Serialize, Deserialize)]", f"pub struct {pascal_case(dm.name)} {{"]
            seen_fields: set[str] = set()
            for field in dm.fields:
                base_name = snake_case(re.sub(r"([a-z0-9])([A-Z])", r"\\1_\\2", field.name))
                if base_name in {"self", "super", "crate"}:
                    base_name += "_"
                rust_name = f"r#{base_name}" if base_name in rust_keywords else base_name
                if base_name in seen_fields:
                    raise ValueError(f"Rust field-name collision in {dm.name!r}: {field.name!r}")
                seen_fields.add(base_name)
                try:
                    typ = _TYPES[field.type]
                except KeyError as exc:
                    raise ValueError(f"Unsupported Rust field type for {dm.name}.{field.name}: {field.type!r}") from exc
                if not field.required:
                    typ = f"Option<{typ}>"
                if base_name != field.name:
                    out.append(f"    #[serde(rename = {json.dumps(field.name, ensure_ascii=False)})]")
                out.append(f"    pub {rust_name}: {typ},")
            out += ["}", ""]
        return "\n".join(out)

    def _lib(self):
        return """pub mod domain;

use axum::{routing::get, Router};

pub fn app() -> Router {
    Router::new().route("/health", get(|| async { "ok" }))
}
"""

    def _main(self, slug):
        crate_name = slug.replace("-", "_")
        return """use __CRATE_NAME__::app;

#[tokio::main]
async fn main() {
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8000").await.expect("bind HTTP listener");
    axum::serve(listener, app()).await.expect("serve HTTP application");
}
""".replace("__CRATE_NAME__", crate_name)

    def _test(self, slug):
        crate_name = slug.replace("-", "_")
        return """use __CRATE_NAME__::app;
use axum::{body::{to_bytes, Body}, http::Request};
use tower::ServiceExt;

#[tokio::test]
async fn health_endpoint_returns_ok() {
    let response = app()
        .oneshot(Request::builder().uri("/health").body(Body::empty()).expect("request"))
        .await.expect("response");
    assert_eq!(response.status(), 200);
    let body = to_bytes(response.into_body(), usize::MAX).await.expect("body");
    assert_eq!(&body[..], b"ok");
}

#[tokio::test]
async fn unknown_route_returns_not_found() {
    let response = app()
        .oneshot(Request::builder().uri("/not-a-route").body(Body::empty()).expect("request"))
        .await.expect("response");
    assert_eq!(response.status(), 404);
}
""".replace("__CRATE_NAME__", crate_name)

    def _dockerfile(self, slug):(self, slug):(self, slug):
        return f"""FROM rust:1.85-slim AS build
WORKDIR /app
COPY . .
RUN cargo test
RUN cargo build --release
FROM debian:bookworm-slim
COPY --from=build /app/target/release/{slug} /usr/local/bin/app
EXPOSE 8000
CMD ["/usr/local/bin/app"]
"""

    def _manifest(self):
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[BundleCapability.BUILD, BundleCapability.TEST,
                BundleCapability.CONTAINERIZE, BundleCapability.HEALTH_CHECK,
                BundleCapability.DOCUMENTATION],
            metadata={"language": "rust", "framework": "axum", "style": "typed-hexagonal"},
        )
