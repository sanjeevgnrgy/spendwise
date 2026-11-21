"""The basic catalog's components SpendWise allows: display (Text, Card, Row, Column, List, Divider), input
(TextField, ChoicePicker, DateTimeInput) and Button.

Part of the assistant's A2UI models (presentation layer). The browser draws each with its own trusted component, so the
agent never sends HTML or code. The classes are Pydantic models, so they're described in `#` comments: a docstring would
become part of their JSON schema.
"""

from typing import Literal

from pydantic import Field

from app.modules.assistant.a2ui.models.actions import Action
from app.modules.assistant.a2ui.models.base import (
    A2uiModel,
    Align,
    ComponentId,
    DataBinding,
    DynamicString,
    Justify,
)


# A line of text: a label, a value, a caption.
class Text(A2uiModel):
    id: ComponentId
    component: Literal["Text"] = "Text"
    text: DynamicString
    variant: Literal["caption", "body"] = "body"  # the spec's only two text styles


# A framed box around one child: every card's and form's root.
class Card(A2uiModel):
    id: ComponentId
    component: Literal["Card"] = "Card"
    child: ComponentId  # exactly one child: put several inside a Column or Row


# Children side by side.
class Row(A2uiModel):
    id: ComponentId
    component: Literal["Row"] = "Row"
    children: list[ComponentId]
    justify: Justify | None = None
    align: Align | None = None


# Children one below the other.
class Column(A2uiModel):
    id: ComponentId
    component: Literal["Column"] = "Column"
    children: list[ComponentId]
    justify: Justify | None = None
    align: Align | None = None


# A list of similar rows (a search's expenses).
class List(A2uiModel):
    id: ComponentId
    component: Literal["List"] = "List"
    children: list[ComponentId]
    direction: Literal["vertical", "horizontal"] | None = None
    align: Align | None = None


# A thin line between parts of a card.
class Divider(A2uiModel):
    id: ComponentId
    component: Literal["Divider"] = "Divider"
    axis: Literal["horizontal", "vertical"] | None = None


# A text input (amount, merchant, note), bound to a field of the data model.
class TextField(A2uiModel):
    id: ComponentId
    component: Literal["TextField"] = "TextField"
    label: str
    value: DynamicString  # bind it, so what the user types lands in the data model
    placeholder: str | None = None
    variant: Literal["shortText", "longText", "number", "obscured"] | None = None


# One choice in a ChoicePicker: what it shows, and the value it stands for.
class ChoiceOption(A2uiModel):
    label: str
    value: str


class ChoicePicker(A2uiModel):
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
class DateTimeInput(A2uiModel):
    id: ComponentId
    component: Literal["DateTimeInput"] = "DateTimeInput"
    label: str
    value: DataBinding  # an ISO 8601 date, "2026-11-13"
    enable_date: Literal[True] = True  # the spec's default is false, so a date picker must say true
    enable_time: Literal[False] | None = None  # dates only: there's no time on an expense


# A button: its label is a child component, and its action names one of ActionName's.
class Button(A2uiModel):
    id: ComponentId
    component: Literal["Button"] = "Button"
    child: ComponentId  # usually a Text: the button's label
    action: Action
    variant: Literal["default", "primary", "borderless"] | None = None
