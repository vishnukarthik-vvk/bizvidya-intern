"""Database engine + session factory.

Replaces the original database.py. Changes:
  - normalises Render's `postgres://` scheme (SQLAlchemy 2.x rejects it)
  - pool_pre_ping / pool_recycle so free-tier Postgres dropping idle
    connections doesn't surface as "SSL connection has been closed unexpectedly"
  - fails loudly at import if DATABASE_URL is unset instead of passing None
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set — check your .env ")

# Render (and Heroku) hand out postgres://, SQLAlchemy 2.x only accepts postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,                       # validate connection before handing it out
    pool_recycle=280,                         # under Render's ~300s idle cutoff
    pool_size=5,
    max_overflow=10,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
