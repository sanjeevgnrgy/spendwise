"""Database migrations (Alembic), run or checked from code (composition layer, beside bootstrap.py).

Tables are never created or changed by the app as it starts. Migrations in backend/migrations do it,
one numbered, reviewed step at a time, so an existing database is changed in place instead of being
deleted and recreated. `.\\run.ps1`, seed.py and mcp_stdio.py run them (upgrade_to_latest); the web app only
checks they've been run (require_latest, from main.py's start-up).
"""

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine

from app.core.config import BACKEND_DIR

ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
# The revision Alembic upgrades to: the newest migration.
HEAD = "head"
# Where upgrade_to_latest hands env.py a connection to migrate (Alembic's documented way to share one).
CONNECTION_ATTRIBUTE = "connection"


def _config() -> Config:
    """Alembic's configuration, from backend/alembic.ini (which points at backend/migrations)."""
    return Config(str(ALEMBIC_INI))


def upgrade_to_latest(engine: Engine | None = None) -> None:
    """Run every migration the database hasn't had yet, in one transaction.

    `engine` is the database to migrate; by default, the one in DATABASE_URL. The whole upgrade is atomic (see
    backend/migrations/env.py): if any step fails, the database is left exactly as it was, and the error is raised.
    """
    config = _config()
    if engine is None:
        command.upgrade(config, HEAD)
        return
    # One transaction around the whole upgrade, committed only if every migration succeeds.
    with engine.begin() as connection:
        config.attributes[CONNECTION_ATTRIBUTE] = connection
        command.upgrade(config, HEAD)


def require_latest(engine: Engine) -> None:
    """Refuse to start on a database whose tables are out of date, with the fix in the message.

    Raises RuntimeError if the database behind `engine` isn't at the newest migration.
    """
    head = ScriptDirectory.from_config(_config()).get_current_head()
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    if current != head:
        raise RuntimeError(
            f"The database is at migration {current or 'none'}, but the code needs {head}. "
            "Run the migrations: .\\run.ps1 does it, or "
            ".\\.venv\\Scripts\\python.exe -m alembic -c backend\\alembic.ini upgrade head"
        )
