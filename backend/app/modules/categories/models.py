from sqlmodel import Field, SQLModel


class Category(SQLModel, table=True):
    """The categories table. Private to this module: other modules never import it."""

    id: int | None = Field(default=None, primary_key=True)
    # Unique, so people and the AI can refer to a category by its name.
    name: str = Field(max_length=50, unique=True, index=True)
    # An icon name (e.g. "utensils") that the frontend maps to a picture, not an emoji,
    # so it stays plain text everywhere it's stored or printed.
    icon: str = Field(max_length=50)
