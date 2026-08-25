from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import os

# Ensure directory exists
os.makedirs("data", exist_ok=True)

DATABASE_URL = "sqlite:///data/evolution.db"

# Optimized engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False  # Set to True for SQL debugging
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@contextmanager
def get_db_session():
    """Context manager for database sessions - ensures proper cleanup"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db():
    """Dependency for FastAPI routes - provides automatic session cleanup"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from app.storage.models import GenomeRecord, EvolutionRun
    Base.metadata.create_all(bind=engine)
