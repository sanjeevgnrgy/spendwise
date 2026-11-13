from typing import Annotated, Any

from pydantic import Field
from sqlalchemy import event
from sqlmodel import Session, create_engine

from app.core.config import settings

IS_SQLITE = settings.database_url.startswith("sqlite")

# SQLite normally lets only the thread that opened a connection use it, but FastAPI runs
# plain `def` routes in a thread pool. Other databases (Postgres) don't need this option.
_connect_args = {"check_same_thread": False} if IS_SQLITE else {}

# One engine for the whole app: it manages the pool of database connections.
engine = create_engine(settings.database_url, connect_args=_connect_args)

if IS_SQLITE:
    # Python's sqlite3 driver manages transactions itself, and gets two things wrong for us: it commits
    # schema changes (CREATE, ALTER, DROP) immediately, so a migration that fails halfway stays half done,
    # and it breaks SAVEPOINTs. SQLAlchemy's documented fix: turn the driver's handling off, and start
    # every transaction ourselves. https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl
    @event.listens_for(engine, "connect")
    def _driver_hands_off(dbapi_connection: Any, connection_record: Any) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(connection: Any) -> None:
        connection.exec_driver_sql("BEGIN")


# The largest integer SQLite can store. Ids above it can't exist, so inputs are capped here and get a
# clean 404/422, instead of crashing the database driver with an OverflowError (a 500).
MAX_ID = 2**63 - 1
# Any table's id, as callers may send it. (For a URL path, see core/dependencies.IdPath.)
RecordId = Annotated[int, Field(ge=1, le=MAX_ID)]


def new_session() -> Session:
    # The tables are created and changed by migrations (backend/migrations), never by the app itself.
    return Session(engine)
