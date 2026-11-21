"""A2UI messages: createSurface (agent to renderer), with the checks that make a surface drawable, and action
(renderer to agent). Only the messages SpendWise sends and reads are modelled.

Part of the assistant's A2UI models (presentation layer): cards.py and forms.py build these, forms.py checks the model's
own forms against them, and api/agui_request.py reads button clicks (ActionMessage). The classes are Pydantic models, so
they're described in `#` comments: a docstring would become part of their JSON schema.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.assistant.a2ui.models.base import (
    A2UI_VERSION,
    MAX_USER_MESSAGE_LENGTH,
    ROOT_ID,
    A2uiModel,
    ActionName,
    Catalog,
    ComponentId,
    SurfaceId,
)
from app.modules.assistant.a2ui.models.basic import (
    Button,
    Card,
    ChoicePicker,
    Column,
    DateTimeInput,
    Divider,
    List,
    Row,
    Text,
    TextField,
)
from app.modules.assistant.a2ui.models.insights import Chart, Stat

# The "component" field says which model applies, so Pydantic checks each one against the right rules.
Component = Annotated[
    Text | Card | Row | Column | List | Button | Divider | TextField | ChoicePicker | DateTimeInput | Chart | Stat,
    Field(discriminator="component"),
]


def _referenced_ids(component: BaseModel) -> list[str]:
    """The ids a component points at: its `children`, or its one `child`, or none."""
    child = getattr(component, "child", None)
    return getattr(component, "children", None) or ([child] if child else [])


# A new surface: its id, catalog, every component, and optionally its starting data.
class CreateSurface(A2uiModel):
    surface_id: SurfaceId
    catalog_id: str = Catalog.BASIC
    components: list[Component] = Field(min_length=1)
    # The surface's starting data, e.g. a form pre-filled with what the agent understood.
    data_model: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _complete(self) -> CreateSurface:
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
class _Message(A2uiModel):
    version: Literal["1.0"] = A2UI_VERSION

    def to_json(self) -> dict[str, Any]:
        """The wire format: camelCase keys, and no nulls for options that weren't set."""
        return self.model_dump(by_alias=True, exclude_none=True)


class CreateSurfaceMessage(_Message):
    """Creates a surface (one self-contained piece of UI), here together with all its components."""

    create_surface: CreateSurface


class UserAction(A2uiModel):
    """A button was clicked. `context` holds the values its bindings pointed at, read at the click."""

    name: ActionName
    surface_id: SurfaceId
    source_component_id: ComponentId
    timestamp: str  # ISO 8601, when it was clicked
    # Strings, or lists of strings from a ChoicePicker. Never trusted: it's what the user typed.
    context: dict[str, str | list[str] | bool | int | float | None]
    user_message: str | None = Field(default=None, max_length=MAX_USER_MESSAGE_LENGTH)


# The message a click arrives in (forwardedProps.a2uiAction): the version, and the action itself.
class ActionMessage(A2uiModel):
    version: Literal["1.0"]
    action: UserAction
