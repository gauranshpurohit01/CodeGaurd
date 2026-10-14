"""SQLAlchemy database connection and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_FILE = BACKEND_DIR / "codeguard.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_FILE.as_posix()}")

# For SQLite, check_same_thread=False is needed for multi-threaded access
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
