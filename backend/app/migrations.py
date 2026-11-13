"""Database migrations (Alembic), run from code.

Tables are never created or changed by the app as it starts. Migrations in backend/migrations do it,
one numbered, reviewed step at a time, so an existing database is changed in place instead of being
deleted and recreated. `.\\run.ps1` and seed.py run them; the app only checks they've been run.
"""

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from app.core.config import BACKEND_DIR
from app.core.db import engine

ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def _config() -> Config:
    return Config(str(ALEMBIC_INI))


def upgrade_to_latest() -> None:
    command.upgrade(_config(), "head")


def require_latest() -> None:
    """Refuse to start on a database whose tables are out of date, with the fix in the message."""
    head = ScriptDirectory.from_config(_config()).get_current_head()
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    if current != head:
        raise RuntimeError(
            f"The database is at migration {current or 'none'}, but the code needs {head}. "
            "Run the migrations: .\\run.ps1 does it, or .\\.venv\\Scripts\\python.exe -m alembic -c backend\\alembic.ini upgrade head"
        )
