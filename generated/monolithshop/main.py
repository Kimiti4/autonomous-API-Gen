"""
Main application entry point.
Auto-generated from ISR.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from monolithshop.config import settings
from monolithshop.infrastructure.database import init_db


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


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.app_version}


@app.on_event("startup")
async def startup():
    await init_db()
