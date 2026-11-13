"""A2UI v1.0 messages, and the components SpendWise allows (a subset of the basic catalog).

A2UI describes UI as data: a flat list of components that point at each other by id, starting from
the one with id "root". The browser draws each one with its own trusted components, so the agent
never sends HTML or code. Spec facts and links: docs/sources.md, section 8.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

A2UI_VERSION = "1.0"
# The catalog our components come from. A surface names it so the renderer knows how to read them.
BASIC_CATALOG_ID = "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json"
# SpendWise's own catalog, for what the basic one doesn't have (Chart, Stat). A catalog can't extend
# another, so its components sit on basic-catalog surfaces and name their catalog with "@catalogId".
# The id is just a name ("not a resolvable URI", says the spec); a URN doesn't pose as a web address.
INSIGHTS_CATALOG_ID = "urn:spendwise:catalog:insights:v1"

# The spec asks for identifier-style ids: letters, digits and underscores, no hyphens.
ComponentId = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
Justify = Literal["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly", "stretch"]
Align = Literal["start", "center", "end", "stretch"]

# The only actions a button may trigger. A form the model writes can't invent new ones (and may only
# use save_expense: the approval buttons are the server's alone, see forms.py).
ActionName = Literal["save_expense", "approve_delete", "cancel_delete"]


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
    user_message: str | None = None


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
    label: str = Field(max_length=40)
    value: float = Field(allow_inf_nan=False)  # NaN or infinity isn't valid JSON, nor a sensible bar


class Chart(_A2uiModel):
    id: ComponentId
    component: Literal["Chart"] = "Chart"
    catalog_id: Literal["urn:spendwise:catalog:insights:v1"] = Field(INSIGHTS_CATALOG_ID, alias="@catalogId")
    chart_type: Literal["bar", "line", "donut"]
    data: list[ChartPoint] = Field(min_length=1, max_length=24)
    unit: str | None = Field(None, max_length=4)  # shown before values, e.g. "₹"


class Stat(_A2uiModel):
    """One number worth noticing: "Spent in November: ₹9,265.85, +12% vs October"."""

    id: ComponentId
    component: Literal["Stat"] = "Stat"
    catalog_id: Literal["urn:spendwise:catalog:insights:v1"] = Field(INSIGHTS_CATALOG_ID, alias="@catalogId")
    label: str
    value: str
    change: str | None = None
    trend: Literal["up", "down", "flat"] | None = None  # which arrow to show next to `change`


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
    surface_id: str
    catalog_id: str = BASIC_CATALOG_ID
    components: list[Component] = Field(min_length=1)
    # The surface's starting data, e.g. a form pre-filled with what the agent understood.
    data_model: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _complete(self) -> "CreateSurface":
        # Catch mistakes here rather than as a half-drawn card in the browser.
        ids = [c.id for c in self.components]
        if len(ids) != len(set(ids)):
            raise ValueError("component ids must be unique")
        if "root" not in ids:
            raise ValueError('a surface needs a component with id "root": rendering starts there')
        missing = {ref for c in self.components for ref in _referenced_ids(c)} - set(ids)
        if missing:
            raise ValueError(f"components refer to ids that don't exist: {sorted(missing)}")
        return self


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
    surface_id: str
    source_component_id: str
    timestamp: str  # ISO 8601, when it was clicked
    # Strings, or lists of strings from a ChoicePicker. Never trusted: it's what the user typed.
    context: dict[str, str | list[str] | bool | int | float | None]
    user_message: str | None = Field(None, max_length=200)


class ActionMessage(_A2uiModel):
    version: Literal["1.0"]
    action: UserAction
