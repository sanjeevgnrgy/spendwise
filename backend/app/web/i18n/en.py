"""The web layer's texts for people, in English: their keys, and the source every other language translates (web).

Only what the web layer itself says: the problem detail for a bug. (Problem titles stay English: clients show the
detail.) hi.py translates it; __init__.py registers the catalog.
"""

from enum import StrEnum

from app.core.i18n import TextValue


class WebText(StrEnum):
    """The web layer's texts, by key."""

    UNEXPECTED = "problems.unexpected"


EN: dict[WebText, TextValue] = {
    # All a client is ever told about a bug: the details go to the server log only.
    WebText.UNEXPECTED: "Something went wrong on the server.",
}
