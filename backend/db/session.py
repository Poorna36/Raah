"""
Database session factory for RAAH Highway Monitoring System
Handles SQLite connection and session management for hackathon demo
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from .models import Base

# Database connection settings - using SQLite for hackathon demo
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./raah.db"
)

# Create engine with SQLite
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Used by FastAPI for dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables based on SQLAlchemy models.
    This should be called during application startup.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables. Use with caution!
    """
    Base.metadata.drop_all(bind=engine)


def get_engine():
    """
    Get the database engine for direct operations.
    """
    return engine