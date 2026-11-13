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

# The spec asks for identifier-style ids: letters, digits and underscores, no hyphens.
ComponentId = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")]
Justify = Literal["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly", "stretch"]
Align = Literal["start", "center", "end", "stretch"]


class _A2uiModel(BaseModel):
    # Python names in snake_case, JSON in camelCase as the spec writes it (surfaceId, createSurface).
    # Unknown fields are an error, as in the spec's schema, so a typo can't slip through to the browser.
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


# ---------- the allowed catalog: Text, Card, Row, Column, List, Button, Divider ----------
# Values are plain literals. The spec also allows data bindings ({"@path": ...}); not needed yet.


class Text(_A2uiModel):
    id: ComponentId
    component: Literal["Text"] = "Text"
    text: str
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


class EventAction(_A2uiModel):
    name: str
    context: dict[str, Any] | None = None


class Action(_A2uiModel):
    # When clicked, the renderer sends this event back to the agent (a later phase handles it).
    event: EventAction


class Button(_A2uiModel):
    id: ComponentId
    component: Literal["Button"] = "Button"
    child: ComponentId  # usually a Text: the button's label
    action: Action
    variant: Literal["default", "primary", "borderless"] | None = None


# The "component" field says which model applies, so Pydantic checks each one against the right rules.
Component = Annotated[Text | Card | Row | Column | List | Button | Divider, Field(discriminator="component")]


def _referenced_ids(component: BaseModel) -> list[str]:
    child = getattr(component, "child", None)
    return getattr(component, "children", None) or ([child] if child else [])


# ---------- messages (agent to renderer) ----------


class CreateSurface(_A2uiModel):
    surface_id: str
    catalog_id: str = BASIC_CATALOG_ID
    components: list[Component] = Field(min_length=1)

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
