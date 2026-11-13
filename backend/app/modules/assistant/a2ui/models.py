"""A2UI v1.0 messages, and the components SpendWise allows (a subset of the basic catalog).

A2UI describes UI as data: a flat list of components that point at each other by id, starting from
the one with id "root". The browser draws each one with its own trusted components, so the agent
never sends HTML or code. Spec facts and links: docs/sources.md, section 8.
"""

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.modules import categories

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


class _A2uiModel(BaseModel):
    # Python names in snake_case, JSON in camelCase as the spec writes it (surfaceId, createSurface).
    # Unknown fields are an error, as in the spec's schema, so a typo can't slip through to the browser.
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class DataBinding(_A2uiModel):
    """A value that lives in the surface's data model, found by a JSON Pointer such as "/expense/amount".

    Inputs show the value at the path and write what the user types back to it (in the browser only).
    We allow only absolute paths made of simple names, which also keeps "__proto__"-style tricks out.
    """

    path: str = Field(alias="@path", pattern=r"^(/[A-Za-z_][A-Za-z0-9_]*)+$")


# A plain string, or a binding to one in the data model.
DynamicString = str | DataBinding


# ---------- the allowed catalog ----------
# Display: Text, Card, Row, Column, List, Divider. Input: TextField, ChoicePicker, DateTimeInput.
# Action: Button.


class Text(_A2uiModel):
    id: ComponentId
    component: Literal["Text"] = "Text"
    text: DynamicString
    variant: Literal["caption", "body"] = "body"  # the spec's only two text styles


class Card(_A2uiModel):
    id: ComponentId
    component: Literal["Card"] = "Card"
    child: ComponentId  # exactly one child: put several inside a Column or Row


class Row(_A2uiModel):
    id: ComponentId
    component: Literal["Row"] = "Row"
    children: list[ComponentId]
    justify: Justify | None = None
    align: Align | None = None


class Column(_A2uiModel):
    id: ComponentId
    component: Literal["Column"] = "Column"
    children: list[ComponentId]
    justify: Justify | None = None
    align: Align | None = None


class List(_A2uiModel):
    id: ComponentId
    component: Literal["List"] = "List"
    children: list[ComponentId]
    direction: Literal["vertical", "horizontal"] | None = None
    align: Align | None = None


class Divider(_A2uiModel):
    id: ComponentId
    component: Literal["Divider"] = "Divider"
    axis: Literal["horizontal", "vertical"] | None = None


class TextField(_A2uiModel):
    id: ComponentId
    component: Literal["TextField"] = "TextField"
    label: str
    value: DynamicString  # bind it, so what the user types lands in the data model
    placeholder: str | None = None
    variant: Literal["shortText", "longText", "number", "obscured"] | None = None


class ChoiceOption(_A2uiModel):
    label: str
    value: str


class ChoicePicker(_A2uiModel):
    """Pick from a list. A2UI's basic catalog has no "Select": this is it, drawn as a dropdown.

    Its value is a list of strings even for a single choice (the spec's rule), e.g. ["Food"].
    """

    id: ComponentId
    component: Literal["ChoicePicker"] = "ChoicePicker"
    label: str
    options: list[ChoiceOption] = Field(min_length=1)
    value: DataBinding
    variant: Literal["mutuallyExclusive"] | None = None  # one choice only; multi-select isn't supported


class DateTimeInput(_A2uiModel):
    id: ComponentId
    component: Literal["DateTimeInput"] = "DateTimeInput"
    label: str
    value: DataBinding  # an ISO 8601 date, "2026-11-13"
    enable_date: Literal[True] = True  # the spec's default is false, so a date picker must say true
    enable_time: Literal[False] | None = None  # dates only: there's no time on an expense


class EventAction(_A2uiModel):
    name: ActionName
    # What to send with the action: bindings are read from the data model at the moment of the click.
    # int before float, or Pydantic would turn an id like 14 into 14.0.
    context: dict[str, DataBinding | str | bool | int | float] | None = None
    # How the click reads in the chat, e.g. "Approve deleting #14" (the spec's userMessage).
    # Capped like UserAction.user_message, so a form can't carry a message its own Save would be refused for.
    user_message: str | None = Field(None, max_length=MAX_USER_MESSAGE_LENGTH)


class Action(_A2uiModel):
    # When clicked, the renderer sends this event back to the agent as an `action` message.
    event: EventAction


class Button(_A2uiModel):
    id: ComponentId
    component: Literal["Button"] = "Button"
    child: ComponentId  # usually a Text: the button's label
    action: Action
    variant: Literal["default", "primary", "borderless"] | None = None


# ---------- SpendWise's insights catalog: Chart and Stat ----------
# Data and labels only: no colours, sizes or code. How a chart looks is the renderer's decision.


class ChartPoint(_A2uiModel):
    label: str = Field(max_length=categories.MAX_NAME_LENGTH)  # points are categories, so: as long as their names
    value: float = Field(allow_inf_nan=False)  # NaN or infinity isn't valid JSON, nor a sensible bar


class Chart(_A2uiModel):
    id: ComponentId
    component: Literal["Chart"] = "Chart"
    catalog_id: Literal[Catalog.INSIGHTS] = Field(Catalog.INSIGHTS, alias="@catalogId")
    chart_type: ChartType
    data: list[ChartPoint] = Field(min_length=1, max_length=MAX_CHART_POINTS)
    unit: str | None = Field(None, max_length=MAX_UNIT_LENGTH)  # shown before values, e.g. "₹"


class Stat(_A2uiModel):
    """One number worth noticing: "Spent in November: ₹9,265.85, +12% vs October"."""

    id: ComponentId
    component: Literal["Stat"] = "Stat"
    catalog_id: Literal[Catalog.INSIGHTS] = Field(Catalog.INSIGHTS, alias="@catalogId")
    label: str = Field(max_length=MAX_STAT_TEXT_LENGTH)
    value: str = Field(max_length=MAX_STAT_TEXT_LENGTH)
    change: str | None = Field(None, max_length=MAX_STAT_TEXT_LENGTH)
    trend: Trend | None = None  # which arrow to show next to `change`


# The "component" field says which model applies, so Pydantic checks each one against the right rules.
Component = Annotated[
    Text | Card | Row | Column | List | Button | Divider | TextField | ChoicePicker | DateTimeInput | Chart | Stat,
    Field(discriminator="component"),
]


def _referenced_ids(component: BaseModel) -> list[str]:
    child = getattr(component, "child", None)
    return getattr(component, "children", None) or ([child] if child else [])


# ---------- messages (agent to renderer) ----------


class CreateSurface(_A2uiModel):
    surface_id: SurfaceId
    catalog_id: str = Catalog.BASIC
    components: list[Component] = Field(min_length=1)
    # The surface's starting data, e.g. a form pre-filled with what the agent understood.
    data_model: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _complete(self) -> "CreateSurface":
        # Catch mistakes here rather than as a half-drawn card in the browser.
        ids = [c.id for c in self.components]
        if len(ids) != len(set(ids)):
            raise ValueError("component ids must be unique")
        if ROOT_ID not in ids:
            raise ValueError(f'a surface needs a component with id "{ROOT_ID}": rendering starts there')
        missing = {ref for c in self.components for ref in _referenced_ids(c)} - set(ids)
        if missing:
            raise ValueError(f"components refer to ids that don't exist: {sorted(missing)}")
        _check_no_cycles({c.id: _referenced_ids(c) for c in self.components})
        return self


def _check_no_cycles(children: dict[str, list[str]]) -> None:
    """Refuse a component that contains itself, directly or through its children: it would draw forever."""
    open_ids: set[str] = set()  # being checked: meeting one again means a loop
    done: set[str] = set()  # checked already (a child shared by two parents is fine)

    def visit(component_id: str) -> None:
        if component_id in done:
            return
        if component_id in open_ids:
            raise ValueError(f"component '{component_id}' contains itself")
        open_ids.add(component_id)
        for child in children.get(component_id, []):
            visit(child)
        open_ids.discard(component_id)
        done.add(component_id)

    visit(ROOT_ID)


class UpdateComponents(_A2uiModel):
    surface_id: str
    components: list[Component] = Field(min_length=1)


class DeleteSurface(_A2uiModel):
    surface_id: str


class _Message(_A2uiModel):
    version: Literal["1.0"] = A2UI_VERSION

    def to_json(self) -> dict[str, Any]:
        """The wire format: camelCase keys, and no nulls for options that weren't set."""
        return self.model_dump(by_alias=True, exclude_none=True)


class CreateSurfaceMessage(_Message):
    """Creates a surface (one self-contained piece of UI), here together with all its components."""

    create_surface: CreateSurface


class UpdateComponentsMessage(_Message):
    update_components: UpdateComponents


class DeleteSurfaceMessage(_Message):
    delete_surface: DeleteSurface


A2uiMessage = CreateSurfaceMessage | UpdateComponentsMessage | DeleteSurfaceMessage


# ---------- messages (renderer to agent) ----------


class UserAction(_A2uiModel):
    """A button was clicked. `context` holds the values its bindings pointed at, read at the click."""

    name: ActionName
    surface_id: SurfaceId
    source_component_id: ComponentId
    timestamp: str  # ISO 8601, when it was clicked
    # Strings, or lists of strings from a ChoicePicker. Never trusted: it's what the user typed.
    context: dict[str, str | list[str] | bool | int | float | None]
    user_message: str | None = Field(None, max_length=MAX_USER_MESSAGE_LENGTH)


class ActionMessage(_A2uiModel):
    version: Literal["1.0"]
    action: UserAction
