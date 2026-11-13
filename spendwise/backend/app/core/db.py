from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# SQLite normally lets only the thread that opened a connection use it, but FastAPI runs
# plain `def` routes in a thread pool. Other databases (Postgres) don't need this option.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

# One engine for the whole app: it manages the pool of database connections.
engine = create_engine(settings.database_url, connect_args=_connect_args)


def create_db_and_tables() -> None:
    # Creates only tables whose models have been imported by now; existing tables are left alone.
    # Core can't import modules, so the caller (main.py, seed.py) imports them first.
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    # A FastAPI dependency: one session per request, closed automatically when the request ends.
    with Session(engine) as session:
        yield session
