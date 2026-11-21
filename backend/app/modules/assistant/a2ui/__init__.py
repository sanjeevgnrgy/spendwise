"""A2UI inside the assistant module: the allowed component catalog, message models, cards and forms.

Presentation, internal to the assistant (other modules don't use it). The AG-UI adapter (api/agui_stream.py) sends cards
and forms to the browser as CUSTOM events, and api/agui_request.py receives button clicks as A2UI actions; the agent
(agent/: agent.py, prompts.py, surfaces.py) uses the show-form tool, its instructions and the "#14" expense references.
models/ holds the shapes; cards.py, summary_card.py, report_card.py and budget_card.py the ready-made cards, forms.py
the form (all written in the request's language); form_tool.py what the model is told about the form (English); parts.py
what cards and forms are built with.
"""

from app.modules.assistant.a2ui.cards import approval_card, card_for
from app.modules.assistant.a2ui.form_tool import FIELDS, SHOW_FORM_TOOL, SHOW_FORM_TOOL_NAME, form_instructions
from app.modules.assistant.a2ui.forms import FormSource, describe_action, expense_form, expense_form_from_call
from app.modules.assistant.a2ui.models import (
    MAX_USER_MESSAGE_LENGTH,
    ActionMessage,
    ActionName,
    Catalog,
    ClientFunction,
    CreateSurfaceMessage,
    UserAction,
)
from app.modules.assistant.a2ui.parts import expense_ref

__all__ = [
    "FIELDS",
    "MAX_USER_MESSAGE_LENGTH",
    "SHOW_FORM_TOOL",
    "SHOW_FORM_TOOL_NAME",
    "ActionMessage",
    "ActionName",
    "Catalog",
    "ClientFunction",
    "CreateSurfaceMessage",
    "FormSource",
    "UserAction",
    "approval_card",
    "card_for",
    "describe_action",
    "expense_form",
    "expense_form_from_call",
    "expense_ref",
    "form_instructions",
]
