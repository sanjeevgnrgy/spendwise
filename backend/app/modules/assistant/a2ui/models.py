"""A2UI v1.0 messages, and the components SpendWise allows (a subset of the basic catalog).

A2UI describes UI as data: a flat list of components that point at each other by id, starting from
the one with id "root". The browser draws each one with its own trusted components, so the agent
never sends HTML or code. Spec facts and links: docs/sources.md, section 8.

Presentation layer, a declarative copy of the spec's schema: cards.py and forms.py build messages from these
models, forms.py checks the model's own forms against them, and api/agui_request.py reads button clicks
(ActionMessage). Only the messages SpendWise sends are modelled: createSurface (agent to renderer) and
action (renderer to agent). backend/scripts/export_contracts.py shares the names and limits with the web app.

The classes below are Pydantic models, so they're described in `#` comments: a docstring would become part of
their JSON schema.
"""

from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.core.months import YearMonth
from app.modules import categories, reports

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


# A line of text: a label, a value, a caption.
class Text(_A2uiModel):
    id: ComponentId
    component: Literal["Text"] = "Text"
    text: DynamicString
    variant: Literal["caption", "body"] = "body"  # the spec's only two text styles


# A framed box around one child: every card's and form's root.
class Card(_A2uiModel):
    id: ComponentId
    component: Literal["Card"] = "Card"
    child: ComponentId  # exactly one child: put several inside a Column or Row


# Children side by side.
class Row(_A2uiModel):
    id: ComponentId
    component: Literal["Row"] = "Row"
    children: list[ComponentId]
    justify: Justify | None = None
    align: Align | None = None


# Children one below the other.
class Column(_A2uiModel):
    id: ComponentId
    component: Literal["Column"] = "Column"
    children: list[ComponentId]
    justify: Justify | None = None
    align: Align | None = None


# A list of similar rows (a search's expenses).
class List(_A2uiModel):
    id: ComponentId
    component: Literal["List"] = "List"
    children: list[ComponentId]
    direction: Literal["vertical", "horizontal"] | None = None
    align: Align | None = None


# A thin line between parts of a card.
class Divider(_A2uiModel):
    id: ComponentId
    component: Literal["Divider"] = "Divider"
    axis: Literal["horizontal", "vertical"] | None = None


# A text input (amount, merchant, note), bound to a field of the data model.
class TextField(_A2uiModel):
    id: ComponentId
    component: Literal["TextField"] = "TextField"
    label: str
    value: DynamicString  # bind it, so what the user types lands in the data model
    placeholder: str | None = None
    variant: Literal["shortText", "longText", "number", "obscured"] | None = None


# One choice in a ChoicePicker: what it shows, and the value it stands for.
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


# A date picker, bound to a field of the data model.
class DateTimeInput(_A2uiModel):
    id: ComponentId
    component: Literal["DateTimeInput"] = "DateTimeInput"
    label: str
    value: DataBinding  # an ISO 8601 date, "2026-11-13"
    enable_date: Literal[True] = True  # the spec's default is false, so a date picker must say true
    enable_time: Literal[False] | None = None  # dates only: there's no time on an expense


# What a button sends back when clicked: the action's name and the values it carries.
class EventAction(_A2uiModel):
    name: ActionName
    # What to send with the action: bindings are read from the data model at the moment of the click.
    # int before float, or Pydantic would turn an id like 14 into 14.0.
    context: dict[str, DataBinding | str | bool | int | float] | None = None
    # How the click reads in the chat, e.g. "Approve deleting #14" (the spec's userMessage).
    # Capped like UserAction.user_message, so a form can't carry a message its own Save would be refused for.
    user_message: str | None = Field(None, max_length=MAX_USER_MESSAGE_LENGTH)


# The functions SpendWise's insights catalog declares for the renderer to run itself (D209). Each one is declared
# rendererOnly and requiresUserActivation: only a person's click runs it, never the agent, and it's never sent to the
# server as an action. The web app runs only these names (its own allow-list).
class ClientFunction(StrEnum):
    # Save one of a month's report downloads (reports.ReportFormat): the renderer fetches it from the reports routes.
    DOWNLOAD_REPORT = "downloadReport"


# downloadReport's arguments: which month, and which file. Only values: the renderer builds the address itself.
class DownloadReportArgs(_A2uiModel):
    month: str = Field(pattern=YearMonth.PATTERN)
    format: reports.ReportFormat


# A call of one of the catalog's functions (the spec's FunctionCall): its name ("@call"), its arguments, and the
# catalog that declares it (a surface's default catalog is the basic one, so the call names ours).
class FunctionCall(_A2uiModel):
    call: Literal[ClientFunction.DOWNLOAD_REPORT] = Field(alias="@call")
    args: DownloadReportArgs
    catalog_id: Literal[Catalog.INSIGHTS] = Catalog.INSIGHTS


# A button's action: the spec's oneOf, an event sent back to the agent or a function the renderer runs. Exactly one.
class Action(_A2uiModel):
    # When clicked, the renderer sends this event back to the agent as an `action` message.
    event: EventAction | None = None
    # When clicked, the renderer runs this function itself (nothing goes to the agent).
    function_call: FunctionCall | None = None

    @model_validator(mode="after")
    def _one_kind(self) -> "Action":
        if (self.event is None) == (self.function_call is None):
            raise ValueError("an action is either an event or a function call")
        return self


# A button: its label is a child component, and its action names one of ActionName's.
class Button(_A2uiModel):
    id: ComponentId
    component: Literal["Button"] = "Button"
    child: ComponentId  # usually a Text: the button's label
    action: Action
    variant: Literal["default", "primary", "borderless"] | None = None


# ---------- SpendWise's insights catalog: Chart and Stat ----------
# Data and labels only: no colours, sizes or code. How a chart looks is the renderer's decision.


# One bar, point or slice of a Chart.
class ChartPoint(_A2uiModel):
    label: str = Field(max_length=categories.MAX_NAME_LENGTH)  # points are categories, so: as long as their names
    value: float = Field(allow_inf_nan=False)  # NaN or infinity isn't valid JSON, nor a sensible bar


# A chart from the insights catalog: data and a unit only; the renderer decides how it looks.
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
    """The ids a component points at: its `children`, or its one `child`, or none."""
    child = getattr(component, "child", None)
    return getattr(component, "children", None) or ([child] if child else [])


# ---------- messages (agent to renderer) ----------


# A new surface: its id, catalog, every component, and optionally its starting data.
class CreateSurface(_A2uiModel):
    surface_id: SurfaceId
    catalog_id: str = Catalog.BASIC
    components: list[Component] = Field(min_length=1)
    # The surface's starting data, e.g. a form pre-filled with what the agent understood.
    data_model: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _complete(self) -> "CreateSurface":
        """Check the surface can be drawn: unique ids, a root, no dangling references, no loops.

        Returns the surface unchanged; raises ValueError (a validation error) saying what's wrong.
        """
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
        """Walk down from `component_id` (depth first), raising ValueError if it leads back to itself."""
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


# The base of a message to the renderer: every one names the A2UI version it follows.
class _Message(_A2uiModel):
    version: Literal["1.0"] = A2UI_VERSION

    def to_json(self) -> dict[str, Any]:
        """The wire format: camelCase keys, and no nulls for options that weren't set."""
        return self.model_dump(by_alias=True, exclude_none=True)


class CreateSurfaceMessage(_Message):
    """Creates a surface (one self-contained piece of UI), here together with all its components."""

    create_surface: CreateSurface


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


# The message a click arrives in (forwardedProps.a2uiAction): the version, and the action itself.
class ActionMessage(_A2uiModel):
    version: Literal["1.0"]
    action: UserAction
