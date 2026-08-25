import os
from typing import Dict, List
from app.engine.genome import Genome


def generate_main_app(genome: Genome) -> str:
    """Generate main FastAPI application file"""
    
    services_imports = "\n".join([
        f"from services.{svc} import router as {svc}_router"
        for svc in genome.services
    ])
    
    services_includes = "\n".join([
        f'app.include_router({svc}_router, prefix="/api/{genome.api_version}/{svc}", tags=["{svc}"])'
        for svc in genome.services
    ])
    
    cors_code = ""
    if genome.cors_enabled:
        cors_code = """
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
"""
    
    auth_middleware = ""
    if genome.auth == "jwt":
        auth_middleware = """

# JWT Authentication middleware placeholder
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # JWT validation would go here
    response = await call_next(request)
    return response
"""
    
    code = f'''"""
Auto-generated API System
Services: {", ".join(genome.services)}
Auth: {genome.auth}
Database: {genome.database}
Cache: {"Enabled" if genome.cache_enabled else "Disabled"}
Rate Limiting: {"Enabled" if genome.rate_limiting else "Disabled"}
"""

from fastapi import FastAPI, Request
{services_imports}

app = FastAPI(
    title="Evolved API System",
    version="{genome.api_version}",
    description="Automatically generated microservice architecture"
)

{cors_code}
{services_includes}

@app.get("/")
async def root():
    return {{
        "message": "Evolved API System",
        "version": "{genome.api_version}",
        "services": {genome.services},
        "auth": "{genome.auth}",
        "database": "{genome.database}"
    }}

@app.get("/health")
async def health_check():
    return {{"status": "healthy"}}
{auth_middleware}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    return code


def generate_service_file(service_name: str, genome: Genome) -> str:
    """Generate individual service module"""
    
    auth_check = ""
    if genome.auth == "jwt":
        auth_check = """
    # JWT token validation would go here
    pass
"""
    
    code = f'''"""
{service_name.upper()} Service
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class {service_name.capitalize()}Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None


# In-memory storage (would be database in production)
items_db = []


@router.get("/")
async def list_items():
    """List all items"""
    {auth_check}
    return {{"items": items_db}}


@router.get("/{{item_id}}")
async def get_item(item_id: int):
    """Get specific item"""
    {auth_check}
    if item_id < len(items_db):
        return items_db[item_id]
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("/")
async def create_item(item: {service_name.capitalize()}Item):
    """Create new item"""
    {auth_check}
    item.id = len(items_db)
    items_db.append(item.dict())
    return item


@router.put("/{{item_id}}")
async def update_item(item_id: int, item: {service_name.capitalize()}Item):
    """Update existing item"""
    {auth_check}
    if item_id < len(items_db):
        item.id = item_id
        items_db[item_id] = item.dict()
        return item
    raise HTTPException(status_code=404, detail="Item not found")


@router.delete("/{{item_id}}")
async def delete_item(item_id: int):
    """Delete item"""
    {auth_check}
    if item_id < len(items_db):
        deleted = items_db.pop(item_id)
        return {{"deleted": deleted}}
    raise HTTPException(status_code=404, detail="Item not found")
'''
    
    return code


def generate_requirements(genome: Genome) -> str:
    """Generate requirements.txt"""
    packages = [
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "pydantic>=2.0.0",
    ]
    
    if genome.database == "postgres":
        packages.append("sqlalchemy>=2.0.0")
        packages.append("psycopg2-binary>=2.9.0")
    elif genome.database == "mysql":
        packages.append("sqlalchemy>=2.0.0")
        packages.append("pymysql>=1.0.0")
    else:
        packages.append("aiosqlite>=0.19.0")
    
    if genome.cache_enabled:
        packages.append("redis>=4.6.0")
    
    if genome.auth == "jwt":
        packages.append("PyJWT>=2.8.0")
        packages.append("python-jose[cryptography]>=3.3.0")
    
    return "\n".join(packages)


def build_genome_output(genome: Genome, output_dir: str = "output/generated_api") -> str:
    """
    Build complete API system from genome.
    Returns the output directory path.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Create services directory
    services_dir = os.path.join(output_dir, "services")
    os.makedirs(services_dir, exist_ok=True)
    
    # Generate main app
    main_code = generate_main_app(genome)
    with open(os.path.join(output_dir, "main.py"), "w") as f:
        f.write(main_code)
    
    # Generate each service
    for service in genome.services:
        service_code = generate_service_file(service, genome)
        with open(os.path.join(services_dir, f"{service}.py"), "w") as f:
            f.write(service_code)
    
    # Create __init__.py for services package
    with open(os.path.join(services_dir, "__init__.py"), "w") as f:
        f.write("# Services package\n")
    
    # Generate requirements.txt
    requirements = generate_requirements(genome)
    with open(os.path.join(output_dir, "requirements.txt"), "w") as f:
        f.write(requirements)
    
    # Generate Dockerfile
    dockerfile = generate_dockerfile(genome)
    with open(os.path.join(output_dir, "Dockerfile"), "w") as f:
        f.write(dockerfile)
    
    # Generate README
    readme = generate_readme(genome)
    with open(os.path.join(output_dir, "README.md"), "w") as f:
        f.write(readme)
    
    return output_dir


def generate_dockerfile(genome: Genome) -> str:
    """Generate Dockerfile for the API"""
    return f'''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
'''


def generate_readme(genome: Genome) -> str:
    """Generate README for the generated API"""
    services_list = "\n".join([f"- `{svc}`: {svc.capitalize()} service" for svc in genome.services])
    
    return f'''# Generated API System

## Configuration
- **Services**: {", ".join(genome.services)}
- **Authentication**: {genome.auth}
- **Database**: {genome.database}
- **Caching**: {"Enabled" if genome.cache_enabled else "Disabled"}
- **Rate Limiting**: {"Enabled" if genome.rate_limiting else "Disabled"}
- **API Version**: {genome.api_version}

## Services
{services_list}

## Running Locally

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## Running with Docker

```bash
docker build -t evolved-api .
docker run -p 8000:8000 evolved-api
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/{genome.api_version}/{{service}}/` - List items for service
- `POST /api/{genome.api_version}/{{service}}/` - Create item
- `GET /api/{genome.api_version}/{{service}}/{{id}}` - Get item
- `PUT /api/{genome.api_version}/{{service}}/{{id}}` - Update item
- `DELETE /api/{genome.api_version}/{{service}}/{{id}}` - Delete item

---
*Generated by Autonomous Evolution Engine*
'''
