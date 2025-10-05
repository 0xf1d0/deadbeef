from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _make_database_url() -> str:
    # Use SQLite by default; allow override via env var
    return os.getenv("DATABASE_URL", "sqlite:///bot.db")


class Base(DeclarativeBase):
    pass


engine = create_engine(_make_database_url(), future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    # Import models so that they are registered with Base before create_all
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "init_db",
]


