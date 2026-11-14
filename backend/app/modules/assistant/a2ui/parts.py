"""What every card and form is built with: fresh surface ids, the message that creates a surface, and "#14".

Presentation layer. Used by the cards (cards.py, summary_card.py) and the form (forms.py); expense_ref() is also
how the agent's instructions (agent/prompts.py) and replies (application/decisions.py) write an expense's id.
"""

from uuid import uuid4

from app.modules.assistant.a2ui.models import Component, CreateSurface, CreateSurfaceMessage

# The random part of a surface id: enough hex digits never to repeat within a chat.
SURFACE_ID_LENGTH = 12


def new_surface_id(prefix: str) -> str:
    """A fresh surface id, e.g. "summary_3f2a9c01b7de": the prefix says what the card is."""
    # The spec forbids creating the same surface twice, and the same expense can be updated (or a month
    # summed up) more than once in a chat, so every card gets a new surface id.
    return f"{prefix}_{uuid4().hex[:SURFACE_ID_LENGTH]}"


def surface(surface_id: str, components: list[Component]) -> CreateSurfaceMessage:
    """The message that creates a card from its components (checked as it's built)."""
    return CreateSurfaceMessage(create_surface=CreateSurface(surface_id=surface_id, components=components))


def expense_ref(expense_id: int) -> str:
    """How an expense's id is written everywhere the user sees it: "#14"."""
    # Shown as "#14" so the user can refer to an expense exactly ("delete #14"); the assistant knows this form.
    return f"#{expense_id}"
