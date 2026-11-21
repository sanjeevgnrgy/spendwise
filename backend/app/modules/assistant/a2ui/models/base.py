"""A2UI's shared vocabulary: the version, the catalogs, the action and chart names, the limits, the id types,
the base model every A2UI model uses, and data-model bindings.

Part of the assistant's A2UI models (presentation layer); the other files of this package build on it, and
backend/scripts/export_contracts.py shares the names and limits with the web app. Spec facts and links: docs/sources.md,
section 8. The classes are Pydantic models, so they're described in `#` comments: a docstring would become part of their
JSON schema.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

A2UI_VERSION = "1.0"
# Rendering starts at the component with this id (the spec's rule).
ROOT_ID = "root"


class Catalog(StrEnum):
    """The component catalogs this app knows. A catalog id is a name, not something to download."""

    # The spec's basic catalog: layout, text, inputs, buttons.
    BASIC = "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
    # SpendWise's own, for what the basic one doesn't have (Chart, Stat). A catalog can't extend
    # another, so its components sit on basic-catalog surfaces and name their catalog with "@catalogId".
    # "Not a resolvable URI", says the spec; a URN doesn't pose as a web address.
    INSIGHTS = "urn:spendwise:catalog:insights:v1"


class ActionName(StrEnum):
    """The only actions a button may trigger. A form the model writes may only use SAVE_EXPENSE."""

    SAVE_EXPENSE = "save_expense"
    APPROVE_DELETE = "approve_delete"
    CANCEL_DELETE = "cancel_delete"


# The kinds of chart a Chart component may draw.
class ChartType(StrEnum):
    BAR = "bar"
    LINE = "line"
    DONUT = "donut"


class Trend(StrEnum):
    """Which arrow a Stat shows next to its change."""

    UP = "up"
    DOWN = "down"
    FLAT = "flat"


# Limits the browser applies too (it gets them from the generated contracts).
MAX_CHART_POINTS = 24
MAX_UNIT_LENGTH = 4
MAX_STAT_TEXT_LENGTH = 60
# Surface ids are ours (card prefix + random hex, or an approval id); anything longer is refused.
SURFACE_ID_MAX_LENGTH = 64
SurfaceId = Annotated[str, Field(min_length=1, max_length=SURFACE_ID_MAX_LENGTH)]

# The spec asks for identifier-style ids: letters, digits and underscores, no hyphens.
ComponentId = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
Justify = Literal["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly", "stretch"]
Align = Literal["start", "center", "end", "stretch"]
MAX_USER_MESSAGE_LENGTH = 200


# The base of every A2UI model: the spec's JSON names, and no unknown fields.
class A2uiModel(BaseModel):
    # Python names in snake_case, JSON in camelCase as the spec writes it (surfaceId, createSurface).
    # Unknown fields are an error, as in the spec's schema, so a typo can't slip through to the browser.
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class DataBinding(A2uiModel):
    """A value that lives in the surface's data model, found by a JSON Pointer such as "/expense/amount".

    Inputs show the value at the path and write what the user types back to it (in the browser only).
    We allow only absolute paths made of simple names, which also keeps "__proto__"-style tricks out.
    """

    path: str = Field(validation_alias="@path", serialization_alias="@path", pattern=r"^(/[A-Za-z_][A-Za-z0-9_]*)+$")


# A plain string, or a binding to one in the data model.
DynamicString = str | DataBinding
