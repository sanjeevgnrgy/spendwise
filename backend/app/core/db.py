"""Database engines and the sessions the bus opens (core infrastructure).

create_db_engine() builds an engine for any SQLAlchemy URL; on SQLite it also sets the engine up so
transactions behave as they do on Postgres: schema changes can be rolled back (atomic migrations) and
SAVEPOINTs work (a command sent from inside another). session_factory() turns an engine into what the bus
(core/cqrs.py) opens one session with per outermost message.

`engine` is the default, for the database in DATABASE_URL: the composition root (bootstrap.build) uses it
unless it's given another engine, and the migrations' env.py runs on it unless handed a connection.
"""

from typing import Any

from sqlalchemy import Engine, StaticPool, event, make_url
from sqlmodel import Session, create_engine

from app.core.config import settings
from app.core.cqrs import SessionFactory

# The backend name SQLAlchemy gives every SQLite URL ("sqlite:///...", "sqlite+pysqlite:///...").
SQLITE_BACKEND = "sqlite"
# How a SQLite URL names a database that lives only in memory ("sqlite://" has no database name at all).
IN_MEMORY_DATABASES = (None, "", ":memory:")


def create_db_engine(url: str) -> Engine:
    """An engine (a pool of connections) for the database at `url`; on SQLite, made fully transactional.

    Creating it doesn't connect yet: the first connection is made on first use.
    """
    parsed = make_url(url)
    is_sqlite = parsed.get_backend_name() == SQLITE_BACKEND
    # SQLite normally lets only the thread that opened a connection use it, but FastAPI runs plain `def`
    # routes in a thread pool. Other databases (Postgres) don't need this option.
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    # An in-memory SQLite database exists only inside its connection, and SQLAlchemy would give each thread its
    # own: every request would see a different, empty database. One shared connection keeps it one database.
    in_memory = is_sqlite and parsed.database in IN_MEMORY_DATABASES
    engine = create_engine(url, connect_args=connect_args, **({"poolclass": StaticPool} if in_memory else {}))
    if is_sqlite:
        # Python's sqlite3 driver manages transactions itself, and gets two things wrong for us: it commits
        # schema changes (CREATE, ALTER, DROP) immediately, so a migration that fails halfway stays half done,
        # and it breaks SAVEPOINTs. SQLAlchemy's documented fix: turn the driver's handling off, and start
        # every transaction ourselves.
        # https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl
        event.listen(engine, "connect", _driver_hands_off)
        event.listen(engine, "begin", _begin)
    return engine


def _driver_hands_off(dbapi_connection: Any, connection_record: Any) -> None:
    """Put each new SQLite connection in the driver's autocommit mode: it never begins or commits on its own."""
    dbapi_connection.isolation_level = None


def _begin(connection: Any) -> None:
    """Send an explicit BEGIN whenever SQLAlchemy starts a transaction, now that the driver doesn't.

    Everything up to the COMMIT or ROLLBACK is then one real SQLite transaction, schema changes included.
    """
    connection.exec_driver_sql("BEGIN")


def session_factory(engine: Engine) -> SessionFactory:
    """The session factory for `engine`: what the composition root hands to the bus."""

    def new_session() -> Session:
        """A new session on the engine, for one unit of work.

        The bus opens one per outermost message and decides when it commits; handlers never open their own.
        """
        # The tables are created and changed by migrations (backend/migrations), never by the app itself.
        return Session(engine)

    return new_session


# The default engine, for the database in DATABASE_URL (see the module docstring for who uses it).
engine = create_db_engine(settings.database_url)
