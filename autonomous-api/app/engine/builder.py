import os
from app.engine.genome import Genome


def generate_main_app(genome: Genome) -> str:
    """Generate a runnable FastAPI application with real shared infrastructure."""
    services_imports = "\n".join(f"from services.{svc} import router as {svc}_router" for svc in genome.services)
    services_includes = "\n".join(f'app.include_router({svc}_router, prefix="/api/{genome.api_version}/{svc}", tags=["{svc}"])' for svc in genome.services)
    cors_code = """
from fastapi.middleware.cors import CORSMiddleware
_allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-API-Key"],
)
""" if genome.cors_enabled else ""
    return f'''"""Generated API architecture. All candidates are expected to run in an isolated environment."""
import os
from fastapi import FastAPI
from database import init_db
{services_imports}
app = FastAPI(title="Evolved API System", version="{genome.api_version}", description="Generated API architecture")
{cors_code}
{services_includes}
@app.get("/")
async def root():
    return {{"message": "Evolved API System", "version": "{genome.api_version}", "services": {genome.services}}}
@app.get("/health")
async def health_check():
    return {{"status": "healthy"}}
@app.on_event("startup")
async def startup():
    init_db()
'''


def generate_database_file(genome: Genome) -> str:
    if genome.database == "sqlite":
        default_url = "sqlite:///./generated.db"
    elif genome.database == "mysql":
        default_url = "mysql+pymysql://user:password@localhost/app"
    else:
        default_url = "postgresql+psycopg2://user:password@localhost/app"
    connect_args = '{"check_same_thread": False}' if genome.database == "sqlite" else "{}"
    return f'''import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
DATABASE_URL = os.getenv("DATABASE_URL", "{default_url}")
engine = create_engine(DATABASE_URL, connect_args={connect_args}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
def init_db():
    from services import models
    Base.metadata.create_all(bind=engine)
'''


def generate_security_file(genome: Genome) -> str:
    """Generate real environment-backed authentication dependencies."""
    return '''import os
import hmac
import jwt
from fastapi import Depends, HTTPException, status
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
        if API_KEY and api_key and hmac.compare_digest(api_key, API_KEY):
            return "api-key"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if AUTH_MODE in {"jwt", "oauth2"}:
        if not credentials or not JWT_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        try:
            jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
            return "bearer"
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if AUTH_MODE == "basic":
        if not basic_credentials or not BASIC_USER or not BASIC_PASSWORD:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        if hmac.compare_digest(basic_credentials.username, BASIC_USER) and hmac.compare_digest(basic_credentials.password, BASIC_PASSWORD):
            return basic_credentials.username
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Basic"})
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unsupported authentication mode")
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
    auth_dep = ", dependencies=[Depends(require_auth)]" if genome.auth else ""
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
    try:
        yield db
    finally:
        db.close()
@router.get("/")
def list_items(db: Session = Depends(get_db)):
    items = db.query({cls}Item).all()
    return {{"items": [{{"id": i.id, "name": i.name, "description": i.description}} for i in items]}}
@router.get("/{{item_id}}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get({cls}Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return {{"id": item.id, "name": item.name, "description": item.description}}
@router.post("/", status_code=201)
def create_item(payload: {cls}Payload, db: Session = Depends(get_db)):
    item = {cls}Item(name=payload.name, description=payload.description)
    db.add(item); db.commit(); db.refresh(item)
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
    if genome.auth in {"jwt", "oauth2"}: packages.append("PyJWT>=2.8.0")
    return "\n".join(packages) + "\n"


def build_genome_output(genome: Genome, output_dir: str = "output/generated_api") -> str:
    os.makedirs(output_dir, exist_ok=True)
    services_dir = os.path.join(output_dir, "services")
    os.makedirs(services_dir, exist_ok=True)
    with open(os.path.join(output_dir, "main.py"), "w") as f: f.write(generate_main_app(genome))
    with open(os.path.join(output_dir, "database.py"), "w") as f: f.write(generate_database_file(genome))
    with open(os.path.join(output_dir, "security.py"), "w") as f: f.write(generate_security_file(genome))
    with open(os.path.join(services_dir, "models.py"), "w") as f: f.write(generate_models_file(genome))
    with open(os.path.join(services_dir, "__init__.py"), "w") as f: f.write("")
    for service in genome.services:
        with open(os.path.join(services_dir, f"{service}.py"), "w") as f: f.write(generate_service_file(service, genome))
    with open(os.path.join(output_dir, "requirements.txt"), "w") as f: f.write(generate_requirements(genome))
    with open(os.path.join(output_dir, "Dockerfile"), "w") as f: f.write(generate_dockerfile(genome))
    with open(os.path.join(output_dir, "README.md"), "w") as f: f.write(generate_readme(genome))
    return output_dir


def generate_dockerfile(genome: Genome) -> str:
    return '''FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]'''
