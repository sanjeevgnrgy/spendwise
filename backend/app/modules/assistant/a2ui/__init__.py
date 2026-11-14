"""A2UI inside the assistant module: the allowed component catalog, message models, cards and forms.

Presentation, internal to the assistant (other modules don't use it). The AG-UI adapter
(api/agui_stream.py) sends cards and forms to the browser as CUSTOM events, and api/agui_request.py
receives button clicks as A2UI actions; the agent (agent/: agent.py, prompts.py, surfaces.py) uses the
show-form tool, its instructions and the "#14" expense references. models.py holds the shapes, cards.py the
ready-made cards, forms.py the form.
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
