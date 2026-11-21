"""The accounts module's write side: table access the commands share (accounts, persistence).

Private to accounts: the commands in commands/ call these. Like every handler's work, they only stage changes in the
bus's session; the bus commits. Times come from the bus's clock (`now`), never the system's.
"""

from sqlalchemy import delete, or_
from sqlmodel import col, select

from app.core.clock import as_utc
from app.core.cqrs import Context
from app.modules.accounts.domain.rules import Profile
from app.modules.accounts.persistence.tables import AppUser, LoginAttempt, UserIdentity, UserSession
from app.modules.accounts.values import LOGIN_ATTEMPT_TTL, MAX_LOGIN_ATTEMPTS

# `moment` as an aware UTC time (SQLite gives stored times back without their zone): core's rule, by its old name.
utc = as_utc


def find_user_id(ctx: Context, issuer: str, subject: str) -> int | None:
    """The user who signs in as `subject` at `issuer`, if they've signed in before."""
    statement = select(UserIdentity.user_id).where(UserIdentity.issuer == issuer, UserIdentity.subject == subject)
    return ctx.session.exec(statement).first()


def add_user(ctx: Context, profile: Profile, issuer: str, subject: str) -> int:
    """A new user, and the identity they signed in with. Returns the user's id."""
    now = ctx.clock.now()
    user = AppUser(
        name=profile.name,
        email=profile.email,
        email_verified=profile.email_verified,
        avatar_url=profile.avatar_url,
        created_at=now,
        updated_at=now,
    )
    ctx.session.add(user)
    # flush sends the INSERT now, so the database assigns the id the identity points at.
    ctx.session.flush()
    assert user.id is not None
    identity = UserIdentity(user_id=user.id, issuer=issuer, subject=subject, email=profile.email, created_at=now)
    ctx.session.add(identity)
    return user.id


def refresh_profile(ctx: Context, user_id: int, profile: Profile) -> AppUser:
    """Store the profile the provider gave at this sign-in, and return the user's row."""
    user = ctx.session.get_one(AppUser, user_id)
    user.name, user.email, user.email_verified = profile.name, profile.email, profile.email_verified
    user.avatar_url = profile.avatar_url
    user.updated_at = ctx.clock.now()
    ctx.session.add(user)
    return user


def forget_ended_sessions(ctx: Context) -> None:
    """Delete every session past its idle or absolute expiry (signed-out ones are kept until then)."""
    now = ctx.clock.now()
    expired = or_(col(UserSession.expires_at) <= now, col(UserSession.absolute_expires_at) <= now)
    ctx.session.execute(delete(UserSession).where(expired))


def forget_old_attempts(ctx: Context) -> None:
    """Delete sign-in attempts older than LOGIN_ATTEMPT_TTL, then all but the newest MAX_LOGIN_ATTEMPTS."""
    cutoff = ctx.clock.now() - LOGIN_ATTEMPT_TTL
    ctx.session.execute(delete(LoginAttempt).where(col(LoginAttempt.created_at) < cutoff))
    newest = select(LoginAttempt.id).order_by(col(LoginAttempt.id).desc()).limit(MAX_LOGIN_ATTEMPTS)
    ctx.session.execute(delete(LoginAttempt).where(col(LoginAttempt.id).not_in(newest)))
