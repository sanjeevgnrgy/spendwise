"""A2UI inside the assistant module: the allowed component catalog, message models, cards and forms.

Presentation, internal to the assistant (other modules don't use it). The AG-UI adapter (agui.py)
sends cards and forms to the browser as CUSTOM events, and receives button clicks as A2UI actions.
"""

from app.modules.assistant.a2ui.cards import approval_card, card_for, expense_ref
from app.modules.assistant.a2ui.forms import (
    SHOW_FORM_TOOL,
    SHOW_FORM_TOOL_NAME,
    FormSource,
    describe_action,
    expense_form_from_call,
    form_instructions,
)
from app.modules.assistant.a2ui.models import (
    MAX_USER_MESSAGE_LENGTH,
    A2uiMessage,
    ActionMessage,
    ActionName,
    Catalog,
    CreateSurfaceMessage,
    UserAction,
)

__all__ = [
    "MAX_USER_MESSAGE_LENGTH",
    "SHOW_FORM_TOOL",
    "SHOW_FORM_TOOL_NAME",
    "A2uiMessage",
    "ActionMessage",
    "ActionName",
    "Catalog",
    "CreateSurfaceMessage",
    "FormSource",
    "UserAction",
    "approval_card",
    "card_for",
    "describe_action",
    "expense_form_from_call",
    "expense_ref",
    "form_instructions",
]
