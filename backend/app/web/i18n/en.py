"""The web layer's texts for people, in English: their keys, and the source every other language translates (web).

Only what the web layer itself says: the problem details it writes when an error's own text isn't for people (a bug,
an outside service's failure) and a validation error's summary. (Problem titles stay English: clients show the
detail.) hi.py translates them; __init__.py registers the catalog.
"""

from enum import StrEnum

from app.core.i18n import TextValue


class WebText(StrEnum):
    """The web layer's texts, by key."""

    UNEXPECTED = "problems.unexpected"
    SERVICE_FAILED = "problems.serviceFailed"
    INVALID_REQUEST = "problems.invalidRequest"


EN: dict[WebText, TextValue] = {
    # All a client is ever told about a bug: the details go to the server log only.
    WebText.UNEXPECTED: "Something went wrong on the server.",
    # A service we depend on (the model, a remote MCP server) failed; its own words go to the server log only.
    WebText.SERVICE_FAILED: "A service the app depends on didn't answer properly. Try again in a moment.",
    # A 422's detail; which values were wrong is in the problem's "errors" list, for the client's developer.
    WebText.INVALID_REQUEST: "Some of the values sent aren't valid.",
}
