"""How Alembic connects to SpendWise's database. Alembic runs this for every migration command."""

from logging.config import fileConfig

from alembic import context

from app.bootstrap import metadata
from app.core.config import settings
from app.core.db import engine

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
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            # All migrations of one `upgrade` run in one transaction, schema changes included (core/db.py makes
            # SQLite honour that): if any step fails, the database is left exactly as it was.
            transactional_ddl=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
