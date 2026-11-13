"""A2UI inside the assistant module: the allowed component catalog, message models and ready-made cards.

Internal to the assistant module (other modules don't use it). The service sends the cards to the
browser as AG-UI CUSTOM events named "a2ui".
"""

from app.modules.assistant.a2ui.cards import card_for
from app.modules.assistant.a2ui.models import A2uiMessage, CreateSurfaceMessage

__all__ = ["A2uiMessage", "CreateSurfaceMessage", "card_for"]
