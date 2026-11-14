"""The conversations module's texts for people, in English: their keys, and the source every other language
translates. Part of the conversations module (i18n/): a thread that isn't there (its own GET /threads/{id}, and the
assistant's /chat). hi.py translates them; __init__.py registers the catalog.
"""

from enum import StrEnum

from app.core.i18n import TextValue


class ConversationText(StrEnum):
    """The conversations module's texts, by key."""

    THREAD_NOT_FOUND = "errors.threadNotFound"


EN: dict[ConversationText, TextValue] = {
    ConversationText.THREAD_NOT_FOUND: "Thread {thread_id} not found",
}
