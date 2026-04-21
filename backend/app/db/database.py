"""
SQLAlchemy engine setup and database initialisation.

init_db() is called once at application startup (via FastAPI lifespan).
It creates the SQLite directory + file and all tables defined in models.py.
Chroma directory setup is handled separately in main.py lifespan.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create SQLite directory + all tables. Safe to call multiple times."""
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    from app.db import models  # noqa: F401 — registers ORM models with Base
    Base.metadata.create_all(bind=engine)
