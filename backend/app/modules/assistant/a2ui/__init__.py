"""A2UI inside the assistant module: the allowed component catalog, message models, cards and forms.

Internal to the assistant module (other modules don't use it). The service sends cards and forms
to the browser as AG-UI CUSTOM events named "a2ui", and receives form submissions as A2UI actions.
"""

from app.modules.assistant.a2ui.cards import card_for
from app.modules.assistant.a2ui.forms import (
    SHOW_FORM_TOOL,
    SHOW_FORM_TOOL_NAME,
    describe_action,
    expense_form_from_call,
    form_instructions,
)
from app.modules.assistant.a2ui.models import A2uiMessage, ActionMessage, CreateSurfaceMessage, UserAction

__all__ = [
    "SHOW_FORM_TOOL",
    "SHOW_FORM_TOOL_NAME",
    "A2uiMessage",
    "ActionMessage",
    "CreateSurfaceMessage",
    "UserAction",
    "card_for",
    "describe_action",
    "expense_form_from_call",
    "form_instructions",
]
