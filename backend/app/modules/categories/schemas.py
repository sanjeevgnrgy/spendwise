from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    """What it takes to create a category."""

    # " Food" and "Food" would look identical in every list, so spaces around the name are removed.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)
    icon: str = Field(min_length=1, max_length=50)


class CategoryRead(CategoryCreate):
    """What other modules get back: a frozen copy, not the table row.

    Handing out a copy means nobody outside this module can change or query
    our table through the object they were given.
    """

    # from_attributes lets us build it straight from a Category row.
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
