"""The categories module's table: `category`.

Private to this module: only its own handlers (commands.py, queries.py) read or write it. Other modules
ask through the contract (contracts.py), and the composition root hands TABLES to the migrations.
The table itself is created and changed by Alembic migrations, never by the app.
"""

from sqlmodel import Field, SQLModel

from app.modules.categories.contracts import MAX_ICON_LENGTH, MAX_NAME_LENGTH


# A SQLModel table class: its docstring stays as it is; notes go in comments.
class Category(SQLModel, table=True):
    """The categories table. Private to this module: other modules never import it."""

    # None until the row is inserted; the database assigns it (see commands.create_category's flush).
    id: int | None = Field(default=None, primary_key=True)
    # Unique, so people and the AI can refer to a category by its name. The index compares the exact
    # text ("Food" and "food" are different to it); create_category also refuses names that differ only
    # in letter case.
    name: str = Field(max_length=MAX_NAME_LENGTH, unique=True, index=True)
    # An icon name the web app maps to a picture (e.g. "utensils"), not an image.
    icon: str = Field(max_length=MAX_ICON_LENGTH)


# Every table this module owns, for the composition root (bootstrap.metadata(), used by the migrations).
TABLES = (Category,)
