"""The web layer's texts for people, in English: their keys, and the source every other language translates (web).

Only what the web layer itself says: the problem details it writes when an error's own text isn't for people (a bug,
an outside service's failure), a validation error's summary, and the refusals of web/auth.py (no session, a request
the app didn't send). (Problem titles stay English: clients show the detail.) hi.py translates them; __init__.py
registers the catalog.
"""

from enum import StrEnum

from app.core.i18n import TextValue


class WebText(StrEnum):
    """The web layer's texts, by key."""

    UNEXPECTED = "problems.unexpected"
    SERVICE_FAILED = "problems.serviceFailed"
    INVALID_REQUEST = "problems.invalidRequest"
    SIGN_IN_REQUIRED = "problems.signInRequired"
    NOT_FROM_APP = "problems.notFromApp"
    TOO_FAST = "problems.tooFast"
    DAILY_LIMIT = "problems.dailyLimit"


EN: dict[WebText, TextValue] = {
    # All a client is ever told about a bug: the details go to the server log only.
    WebText.UNEXPECTED: "Something went wrong on the server.",
    # A service we depend on (the model) failed; its own words go to the server log only.
    WebText.SERVICE_FAILED: "A service the app depends on didn't answer properly. Try again in a moment.",
    # A 422's detail; which values were wrong is in the problem's "errors" list, for the client's developer.
    WebText.INVALID_REQUEST: "Some of the values sent aren't valid.",
    # A 401: no session, or it has ended (expired, signed out). The web app answers it by showing the sign-in page.
    WebText.SIGN_IN_REQUIRED: "Sign in to continue.",
    # A 403 from the X-CSRF check: the request didn't come from the app's own pages.
    WebText.NOT_FROM_APP: "This request didn't come from the app, so it was refused.",
    # 429s from the assistant's rate limit (D194): a minute's allowance, then a day's (the counts reset at midnight UTC).
    WebText.TOO_FAST: "You're sending requests to the assistant too quickly. Wait a minute and try again.",
    WebText.DAILY_LIMIT: "You've reached today's limit for the assistant. Try again tomorrow.",
}
