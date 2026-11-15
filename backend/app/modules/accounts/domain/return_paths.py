"""Where a finished sign-in may send the browser: only back into the web app (accounts module, domain).

The sign-in page passes the page to return to (`return_to`). Taken as it is, it would make the sign-in an "open
redirect": a link to SpendWise's sign-in that ends on another site, which phishing uses. So only a path on the web
app's own origin is kept; anything else becomes the start page. Used by the sign-in use case (application/).
"""

from urllib.parse import urlsplit

from app.modules.accounts.values import MAX_URL_LENGTH, SIGN_IN_PAGE

# Where a sign-in ends when no (acceptable) page was given: the web app's start page.
HOME = "/"
# The characters below the space, and DEL: browsers drop some of them from URLs, which could turn "/\t/evil.com"
# into "//evil.com", another site.
_CONTROL = {chr(code) for code in range(0x20)} | {chr(0x7F)}


def safe_return_path(value: str | None) -> str:
    """`value` if it's a path in the web app, else HOME.

    A path starts with exactly one "/" ("//evil.com" is another host), has no backslash (browsers read "/\\evil.com"
    as "//evil.com"), no control characters, no scheme or host, and isn't the sign-in page itself (a loop).
    """
    if not value or len(value) > MAX_URL_LENGTH or not value.startswith("/") or value.startswith("//"):
        return HOME
    if "\\" in value or any(character in _CONTROL for character in value):
        return HOME
    parts = urlsplit(value)
    if parts.scheme or parts.netloc or parts.path == SIGN_IN_PAGE:
        return HOME
    return value
