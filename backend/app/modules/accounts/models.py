"""The accounts module's read models: frozen copies the queries and commands return, never table rows.

Used by several slices and by the use cases (application/). CurrentUser and SignedInUser are also what
GET /auth/user answers; the rest stay inside the module.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Who is signed in: what the web app shows (name, email, picture). GetCurrentUser returns it.
class CurrentUser(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: int
    name: str | None
    email: str | None
    avatar_url: str | None


# GET /auth/user's answer: the person, and the link that signs this browser out (it carries the session's handle).
class SignedInUser(CurrentUser):
    logout_url: str


# One of the sign-in page's buttons (GET /auth/options): what it sends back as ?option=, and what it says.
class LoginOptionRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    label: str


# A live session, as GetSession finds it: whose it is, its public handle, and when it was last renewed.
class SessionView(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: int
    user_id: int
    handle: str
    renewed_at: datetime


# What the callback checks a sign-in against: TakeLoginAttempt returns it, once.
class LoginAttemptView(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    state: str
    nonce: str
    code_verifier: str
    return_to: str


# What signing out needs from a session: the sealed ID token, to name it to the provider.
class SignOutView(BaseModel):
    model_config = ConfigDict(frozen=True)

    sealed_id_token: str | None
