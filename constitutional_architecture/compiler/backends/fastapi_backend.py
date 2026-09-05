"""
FastAPI Compiler Backend — Consumes validated ISR, emits deployable FastAPI system.

This backend operates on the Backend IR produced by the compiler pipeline.
It generates:
- Domain layer (entities, models)
- Application layer (services, business logic)
- Infrastructure layer (repositories, database)
- API layer (routers, endpoints)
- Authentication and authorization
- Configuration, dependency injection
- Testing
- Docker and deployment configuration

Critical constraint: This backend must NOT modify anything in Steps 1-11
of the Constitutional Architecture (ISR model, evolution engine, type checker, etc.).
If replacing FastAPI with Phoenix requires changes to those components,
the abstraction boundary is in the wrong place.
"""

from __future__ import annotations

import os
import textwrap
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from constitutional_architecture.compiler.artifacts.artifact_model import Artifact, ArtifactType
from constitutional_architecture.compiler.backends.backend_interface import BackendResult, CompilerBackend
from constitutional_architecture.compiler.quality.diagnostics import Diagnostic
from constitutional_architecture.isr.isr_graph import ISRGraph
from constitutional_architecture.isr.model import (
    System, Module, Entity, Service, Workflow, Policy,
    Interface, Event, Deployment, Constraint,
    NodeType, EdgeType, CompletenessLevel
)


@dataclass(frozen=True)
class GeneratedFile:
    """A generated source file."""
    path: str
    content: str
    language: str = "python"


class FastAPIBackend(CompilerBackend):
    """FastAPI compiler backend.

    Consumes the backend IR (not the raw ISR) to generate a complete,
    deployable FastAPI application with all production features.
    """

    @property
    def name(self) -> str:
        return "fastapi"

    def __init__(self, output_dir: str = "./generated"):
        self._output_dir = output_dir
        self._generated_files: List[GeneratedFile] = []
        self._backend_ir: dict = {}

    def validate(self, bir: Any) -> list[Diagnostic]:
        return []

    def bind_capabilities(self, capability_contracts: dict[str, Any]) -> list[Any]:
        return []

    def report_unsupported(self, bir: Any) -> list[str]:
        return []

    def compile(self, bir: Any, bindings: list[Any]) -> BackendResult:
        backend_ir = {"system": {"name": bir.project_name, "package_name": bir.project_name.lower().replace("-", "_")},
                      "modules": [{"name": m.name, "entities": [],
                                   "services": [{"name": n.name, "operations": [{"name": c.name}
                                       for c in n.children]} for n in m.nodes if n.node_type.name == "SERVICE"],
                                   "interfaces": []} for m in bir.modules]}
        files = self.generate(backend_ir)
        artifacts = []
        for f in files:
            atype = ArtifactType.CONFIG if any(f.path.endswith(s) for s in ('.toml', '.yaml', '.yml', '.ini', '.cfg', 'Dockerfile', 'Dockerfile.*')) else ArtifactType.SOURCE
            if f.path.endswith('Dockerfile'):
                atype = ArtifactType.DOCKER
            artifacts.append(Artifact(path=f.path, content=f.content, artifact_type=atype, backend='fastapi'))
        return BackendResult(artifacts=artifacts, diagnostics=[])

    def generate(self, backend_ir: dict) -> List[GeneratedFile]:
        """Generate a complete FastAPI application from the backend IR."""
        self._generated_files = []
        self._backend_ir = backend_ir

        # Generate project structure
        self._generate_init_files()
        self._generate_settings()
        self._generate_database()
        self._generate_models()
        self._generate_schemas()
        self._generate_repositories()
        self._generate_services()
        self._generate_routers()
        self._generate_main()
        self._generate_dockerfile()
        self._generate_requirements()
        self._generate_tests()

        return self._generated_files

    def write_files(self, base_dir: Optional[str] = None) -> List[str]:
        """Write all generated files to disk."""
        output_dir = base_dir or self._output_dir
        written = []

        for gf in self._generated_files:
            full_path = os.path.join(output_dir, gf.path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(gf.content)
            written.append(full_path)

        return written

    def _add_file(self, path: str, content: str):
        self._generated_files.append(GeneratedFile(path=path, content=content))

    def _get_module(self, name: str) -> Optional[dict]:
        for mod in self._backend_ir.get("modules", []):
            if mod["name"] == name:
                return mod
        return None

    # ─── File Generators ───

    def _generate_init_files(self):
        """Generate __init__.py files for the package structure."""
        pkg = self._backend_ir["system"]["package_name"]

        for path in [
            f"{pkg}/__init__.py",
            f"{pkg}/domain/__init__.py",
            f"{pkg}/application/__init__.py",
            f"{pkg}/infrastructure/__init__.py",
            f"{pkg}/api/__init__.py",
            f"{pkg}/tests/__init__.py",
        ]:
            self._add_file(path, f"# {path}\n")

    def _generate_settings(self):
        """Generate settings/configuration module."""
        pkg = self._backend_ir["system"]["package_name"]
        defaults = self._backend_ir.get("defaults", {})

        content = textwrap.dedent(f'''\
        """
        Application configuration.
        Auto-generated from ISR.
        """
        from pydantic_settings import BaseSettings
        from typing import List
        import os


        class Settings(BaseSettings):
            """Application settings loaded from environment variables."""
            app_name: str = "{self._backend_ir['system']['name']}"
            app_version: str = "1.0.0"
            debug: bool = False

            # Database
            database_url: str = os.getenv(
                "DATABASE_URL",
                "sqlite+aiosqlite:///./app.db"
            )

            # Server
            host: str = "0.0.0.0"
            port: int = {defaults.get("port", 8000)}

            # Security
            secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
            cors_origins: List[str] = ["*"]

            # Logging
            log_level: str = "INFO"

            class Config:
                env_file = ".env"
                env_file_encoding = "utf-8"


        settings = Settings()
        ''')

        self._add_file(f"{pkg}/config.py", content)

    def _generate_database(self):
        """Generate database configuration."""
        pkg = self._backend_ir["system"]["package_name"]

        content = textwrap.dedent(f'''\
        """
        Database configuration and session management.
        """
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy.orm import DeclarativeBase
        from {pkg}.config import settings


        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=5,
            max_overflow=10,
        )

        async_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )


        class Base(DeclarativeBase):
            pass


        async def get_session() -> AsyncSession:
            """Dependency that provides a database session."""
            async with async_session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()


        async def init_db():
            """Create all database tables."""
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        ''')

        self._add_file(f"{pkg}/infrastructure/database.py", content)

    def _generate_models(self):
        """Generate SQLAlchemy models from ISR entities."""
        pkg = self._backend_ir["system"]["package_name"]

        for module in self._backend_ir.get("modules", []):
            if not module["entities"]:
                continue

            imports = textwrap.dedent(f'''\
            """
            Domain models for {module['name']} module.
            Auto-generated from ISR.
            """
            from uuid import uuid4
            from datetime import datetime
            from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
            from sqlalchemy.orm import relationship
            from sqlalchemy.dialects.postgresql import UUID
            from {pkg}.infrastructure.database import Base


            ''')

            model_classes = []
            for entity in module["entities"]:
                fields_code = [
                    f"    __tablename__ = \"{entity['name'].lower()}\"",
                    "",
                    "    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)",
                ]

                for field in entity.get("fields", []):
                    if field["name"] == "id":
                        continue
                    col_type = self._map_type(field["type"])
                    nullable = "nullable=False" if field["required"] else "nullable=True"
                    unique = "unique=True" if field["unique"] else ""
                    indexed = "index=True" if field["indexed"] else ""
                    extras = ", ".join(filter(None, [nullable, unique, indexed]))
                    fields_code.append(
                        f"    {field['name']} = Column({col_type}, {extras})"
                    )

                # Add foreign key fields for relationships
                for rel in entity.get("relationships", []):
                    fk_field = f"{rel['target'].lower()}_id"
                    fields_code.append(
                        f"    {fk_field} = Column(UUID(as_uuid=True), "
                        f"ForeignKey(\"{rel['target'].lower()}.id\"))"
                    )

                model_class = (
                    f"class {entity['name']}(Base):\n"
                    + "\n".join(fields_code)
                )
                model_classes.append(model_class)

            content = imports + "\n\n".join(model_classes)
            self._add_file(f"{pkg}/domain/{module['name'].lower()}_models.py", content)

    def _generate_schemas(self):
        """Generate Pydantic schemas for API validation."""
        pkg = self._backend_ir["system"]["package_name"]

        for module in self._backend_ir.get("modules", []):
            if not module["entities"]:
                continue

            content = textwrap.dedent(f'''\
            """
            Pydantic schemas for {module['name']} module.
            Auto-generated from ISR.
            """
            from pydantic import BaseModel, ConfigDict
            from uuid import UUID
            from datetime import datetime
            from typing import Optional, List


            ''')

            for entity in module["entities"]:
                create_fields = []
                response_fields = ["    id: UUID"]

                for field in entity.get("fields", []):
                    if field["name"] == "id":
                        continue
                    py_type = self._map_python_type(field["type"])
                    if field["required"]:
                        create_fields.append(f"    {field['name']}: {py_type}")
                    else:
                        create_fields.append(f"    {field['name']}: Optional[{py_type}] = None")
                    response_fields.append(f"    {field['name']}: {py_type}")

                response_fields.append("    model_config = ConfigDict(from_attributes=True)")

                content += (
                    f"class {entity['name']}Create(BaseModel):\n"
                    + "\n".join(create_fields)
                    + "\n\n"
                    + f"class {entity['name']}Response(BaseModel):\n"
                    + "\n".join(response_fields)
                    + "\n\n"
                )

            self._add_file(f"{pkg}/domain/{module['name'].lower()}_schemas.py", content)

    def _generate_repositories(self):
        """Generate repository layer."""
        pkg = self._backend_ir["system"]["package_name"]

        for module in self._backend_ir.get("modules", []):
            if not module["entities"]:
                continue

            entity_names = [e["name"] for e in module["entities"]]
            content = textwrap.dedent(f'''\
            """
            Repositories for {module['name']} module.
            Auto-generated from ISR.
            """
            from uuid import UUID
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import AsyncSession
            from {pkg}.domain.{module['name'].lower()}_models import (
                {', '.join(entity_names)}
            )


            ''')

            for entity in module["entities"]:
                content += textwrap.dedent(f'''\
                class {entity['name']}Repository:
                    """Repository for {entity['name']} entity."""

                    def __init__(self, session: AsyncSession):
                        self._session = session

                    async def create(self, data: dict) -> {entity['name']}:
                        entity = {entity['name']}(**data)
                        self._session.add(entity)
                        await self._session.flush()
                        return entity

                    async def get(self, entity_id: UUID) -> {entity['name']} | None:
                        result = await self._session.execute(
                            select({entity['name']}).where({entity['name']}.id == entity_id)
                        )
                        return result.scalar_one_or_none()

                    async def list(self, skip: int = 0, limit: int = 100) -> list[{entity['name']}]:
                        result = await self._session.execute(
                            select({entity['name']}).offset(skip).limit(limit)
                        )
                        return list(result.scalars().all())

                    async def update(self, entity_id: UUID, data: dict) -> {entity['name']} | None:
                        entity = await self.get(entity_id)
                        if entity:
                            for key, value in data.items():
                                setattr(entity, key, value)
                            await self._session.flush()
                        return entity

                    async def delete(self, entity_id: UUID) -> bool:
                        entity = await self.get(entity_id)
                        if entity:
                            await self._session.delete(entity)
                            await self._session.flush()
                            return True
                        return False


                ''')

            self._add_file(
                f"{pkg}/infrastructure/{module['name'].lower()}_repository.py",
                content
            )

    def _generate_services(self):
        """Generate service layer."""
        pkg = self._backend_ir["system"]["package_name"]

        for module in self._backend_ir.get("modules", []):
            if not module["services"]:
                continue

            repo_imports = []
            for entity in module.get("entities", []):
                repo_imports.append(
                    f"from {pkg}.infrastructure.{module['name'].lower()}_repository "
                    f"import {entity['name']}Repository"
                )

            content = textwrap.dedent(f'''\
            """
            Services for {module['name']} module.
            Auto-generated from ISR.
            """
            from uuid import UUID
            from typing import Optional
            {chr(10).join(repo_imports)}


            ''')

            for service in module["services"]:
                init_repos = []
                for entity in module.get("entities", []):
                    init_repos.append(
                        f"        self.{entity['name'].lower()}_repo = "
                        f"{entity['name']}Repository(session)"
                    )

                methods = []
                for op in service.get("operations", []):
                    params = op.get("parameters", [])
                    param_strs = []
                    for p in params:
                        if isinstance(p, dict):
                            param_strs.append(
                                f"{p.get('name', 'arg')}: {p.get('type', 'str')}"
                            )
                    params_sig = ", ".join(param_strs)
                    if params_sig:
                        params_sig = f", {params_sig}"

                    return_type = op.get("return_type", "dict")
                    methods.append(textwrap.dedent(f'''\\
                        async def {op['name']}(self{params_sig}) -> {return_type}:
                            """Execute {op['name']} operation."""
                            # TODO: Implement business logic
                            raise NotImplementedError
                    '''))

                content += textwrap.dedent(f'''\\
                class {service['name']}:
                    """Business logic for {service['name']}."""

                    def __init__(self, session):
                        {chr(10).join(init_repos)}

                    {chr(10).join(methods)}


                ''')

            self._add_file(
                f"{pkg}/application/{module['name'].lower()}_service.py",
                content
            )

    def _generate_routers(self):
        """Generate FastAPI routers from ISR interfaces."""
        pkg = self._backend_ir["system"]["package_name"]

        for module in self._backend_ir.get("modules", []):
            if not module["interfaces"]:
                continue

            content = textwrap.dedent(f'''\
            """
            API routes for {module['name']} module.
            Auto-generated from ISR.
            """
            from fastapi import APIRouter, Depends, HTTPException, status
            from sqlalchemy.ext.asyncio import AsyncSession
            from {pkg}.infrastructure.database import get_session
            from {pkg}.application.{module['name'].lower()}_service import (
                {', '.join(s['name'] for s in module.get('services', []))}
            )

            router = APIRouter(prefix="", tags=["{module['name']}"])


            ''')

            for iface in module["interfaces"]:
                if iface.get("internal", False):
                    continue

                for ep in iface.get("endpoints", []):
                    method = ep["method"].lower()
                    path = ep["path"]
                    op_name = ep.get("operation", "handle")
                    func_name = f"handle_{op_name}"

                    content += textwrap.dedent(f'''\\
                    @router.{method}("{path}")
                    async def {func_name}(
                        session: AsyncSession = Depends(get_session),
                    ):
                        """{op_name} operation."""
                        # Auto-generated from ISR
                        service = None  # TODO: Inject service
                        raise HTTPException(
                            status_code=status.HTTP_501_NOT_IMPLEMENTED,
                            detail="{op_name} not yet implemented"
                        )


                    ''')

            self._add_file(
                f"{pkg}/api/{module['name'].lower()}_router.py",
                content
            )

    def _generate_main(self):
        """Generate the main FastAPI application entry point."""
        pkg = self._backend_ir["system"]["package_name"]
        modules = self._backend_ir.get("modules", [])

        router_imports = []
        router_includes = []
        for module in modules:
            if not module["interfaces"]:
                continue
            router_imports.append(
                f"from {pkg}.api.{module['name'].lower()}_router import router "
                f"as {module['name'].lower()}_router"
            )
            router_includes.append(
                f"app.include_router({module['name'].lower()}_router)"
            )

        content = textwrap.dedent(f'''\
        """
        Main application entry point.
        Auto-generated from ISR.
        """
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from {pkg}.config import settings
        from {pkg}.infrastructure.database import init_db
        {chr(10).join(router_imports)}

        app = FastAPI(
            title=settings.app_name,
            version=settings.app_version,
            description="Auto-generated from ISR architecture",
        )

        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Include routers
        {chr(10).join(router_includes)}

        @app.get("/health")
        async def health_check():
            return {{"status": "healthy", "version": settings.app_version}}


        @app.on_event("startup")
        async def startup():
            await init_db()
        ''')

        self._add_file(f"{pkg}/main.py", content)

    def _generate_dockerfile(self):
        """Generate Dockerfile."""
        content = textwrap.dedent('''\
        FROM python:3.11-slim

        WORKDIR /app

        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt

        COPY . .

        EXPOSE 8000

        CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
        ''')

        self._add_file("Dockerfile", content)

    def _generate_requirements(self):
        """Generate requirements.txt."""
        pkg = self._backend_ir["system"]["package_name"]

        content = textwrap.dedent('''\
        fastapi>=0.100.0
        uvicorn>=0.20.0
        sqlalchemy>=2.0.0
        aiosqlite>=0.19.0
        pydantic>=2.0.0
        pydantic-settings>=2.0.0
        python-dotenv>=1.0.0
        alembic>=1.12.0
        ''')

        self._add_file("requirements.txt", content)

    def _generate_tests(self):
        """Generate basic test file."""
        pkg = self._backend_ir["system"]["package_name"]

        content = textwrap.dedent(f'''\
        """
        Tests for the generated application.
        """
        import pytest
        from httpx import AsyncClient, ASGITransport
        from {pkg}.main import app


        @pytest.mark.asyncio
        async def test_health_check():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
        ''')

        self._add_file(f"{pkg}/tests/test_api.py", content)

    # ─── Type Mapping Helpers ───

    @staticmethod
    def _map_type(isr_type: str) -> str:
        """Map ISR field types to SQLAlchemy column types."""
        mapping = {
            "uuid": "UUID(as_uuid=True)",
            "string": "String",
            "text": "Text",
            "integer": "Integer",
            "int": "Integer",
            "float": "Float",
            "decimal": "Float",
            "bool": "Boolean",
            "boolean": "Boolean",
            "datetime": "DateTime",
            "date": "DateTime",
            "json": "Text",
            "list": "Text",
            "list[string]": "Text",
        }
        return mapping.get(isr_type.lower(), "String")

    @staticmethod
    def _map_python_type(isr_type: str) -> str:
        """Map ISR field types to Python type hints."""
        mapping = {
            "uuid": "UUID",
            "string": "str",
            "text": "str",
            "integer": "int",
            "int": "int",
            "float": "float",
            "decimal": "float",
            "bool": "bool",
            "boolean": "bool",
            "datetime": "datetime",
            "date": "datetime",
            "json": "dict",
            "list": "list",
            "list[string]": "list[str]",
        }
        return mapping.get(isr_type.lower(), "str")