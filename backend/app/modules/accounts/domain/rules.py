"""The accounts module's business rules: what a sign-in keeps of a profile, and who may sign in (domain).

Used by the sign-in use case (application/sign_in.py) before it sends SignIn, and by SignIn's handler (an account
that's switched off). The provider's claims are only trusted to be what they say they are: a name is cut to size, an
email that doesn't fit is dropped rather than cut (a cut email is someone else's), and a picture is kept only as an
http(s) URL, because the web app will show it as an image.
"""

from dataclasses import dataclass
from urllib.parse import urlsplit

from app.core.errors import BusinessRuleError
from app.core.identity import VerifiedLogin
from app.modules.accounts.values import MAX_EMAIL_LENGTH, MAX_NAME_LENGTH, MAX_URL_LENGTH

# The only schemes a picture's URL may have: no javascript:, data: or file: URLs reach an <img>.
PICTURE_SCHEMES = ("https", "http")


class AccountDisabledError(BusinessRuleError):
    """The person signed in at the provider, but their SpendWise account is switched off (app_user.is_active)."""


@dataclass(frozen=True)
class Profile:
    """What SpendWise keeps of a person's profile: their name, email (and whether it's verified) and picture."""

    name: str | None
    email: str | None
    email_verified: bool
    avatar_url: str | None


def _picture(url: str | None) -> str | None:
    """`url` if it's an http(s) URL with a host that fits the column, else None."""
    if url is None or len(url) > MAX_URL_LENGTH:
        return None
    parts = urlsplit(url)
    return url if parts.scheme in PICTURE_SCHEMES and parts.netloc else None


def profile_of(login: VerifiedLogin) -> Profile:
    """The profile to keep from a verified sign-in, every value fitted to its column (see the module docstring)."""
    name = login.name.strip()[:MAX_NAME_LENGTH] if login.name else None
    email = login.email if login.email and len(login.email) <= MAX_EMAIL_LENGTH else None
    return Profile(
        name=name or None,
        email=email,
        email_verified=login.email_verified and email is not None,
        avatar_url=_picture(login.picture),
    )


def may_sign_in(roles: frozenset[str], required_role: str | None) -> bool:
    """Whether someone with `roles` may use SpendWise: anyone if no role is required (OIDC_REQUIRED_ROLE unset)."""
    return required_role is None or required_role in roles
