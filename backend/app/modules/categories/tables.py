from sqlmodel import Field, SQLModel

from app.modules.categories.contracts import MAX_ICON_LENGTH, MAX_NAME_LENGTH


class Category(SQLModel, table=True):
    """The categories table. Private to this module: other modules never import it."""

    id: int | None = Field(default=None, primary_key=True)
    # Unique, so people and the AI can refer to a category by its name.
    name: str = Field(max_length=MAX_NAME_LENGTH, unique=True, index=True)
    icon: str = Field(max_length=MAX_ICON_LENGTH)


TABLES = (Category,)
