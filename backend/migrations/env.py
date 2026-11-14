"""How Alembic connects to SpendWise's database (migrations layer).

Alembic runs this for every migration command, from the command line (`alembic -c backend/alembic.ini ...`)
or from code (infrastructure/migrations.upgrade_to_latest, used by seed.py and mcp_stdio.py). It runs on the connection
upgrade_to_latest hands it, if any, else on the default engine (infrastructure/db.engine, the database in DATABASE_URL),
and compares against every module's tables, which the composition root collects (bootstrap.metadata).
"""

from logging.config import fileConfig

from alembic import context

from sqlalchemy import Connection

from app.bootstrap import metadata
from app.infrastructure.config import settings
from app.infrastructure.db import engine
from app.infrastructure.migrations import CONNECTION_ATTRIBUTE

config = context.config
# Only on the command line: when the app runs migrations (seed.py), its own logging setup stays.
if config.cmd_opts is not None and config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Every module's tables, so `alembic revision --autogenerate` can compare them with the database.
target_metadata = metadata()


def run_migrations_offline() -> None:
    """Write the SQL out instead of running it (alembic upgrade head --sql), e.g. for review."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        # SQLite can't change most of a table in place; "batch" mode copies it into a new one instead.
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run the migrations against the database, all of one command in a single transaction.

    If any step fails, everything is rolled back and the error is raised: the database is left as it was.
    """
    given = config.attributes.get(CONNECTION_ATTRIBUTE)
    if given is not None:
        # From app/migrations.upgrade_to_latest(engine): migrate that database, inside its transaction.
        _run_on(given)
        return
    with engine.connect() as connection:
        _run_on(connection)


def _run_on(connection: Connection) -> None:
    """Run this command's migrations on `connection`, all in one transaction."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        # All migrations of one `upgrade` run in one transaction, schema changes included (infrastructure/db.py makes
        # SQLite honour that: its driver needs an explicit BEGIN for transactional DDL).
        transactional_ddl=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
