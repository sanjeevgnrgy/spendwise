"""The rate limit on the routes that call the language model (web layer, D194): POST /agent, /chat, /parse and
/receipts/{id}/extraction each spend model quota, so each person gets a minute's and a day's allowance.

Used by those routes' HTTP adapters (assistant/api/routes.py, receipts/api.py) as a dependency, after the session
check: the count is the signed-in person's. The limiter itself (core/rate_limit.py) is built by the composition root
from the settings and put on `app.state` by main.py. A refusal is a 429 problem with Retry-After, in the request's
language.
"""

from fastapi import Depends, Request

from app.core.errors import TooManyRequestsError
from app.core.i18n import translatable
from app.core.rate_limit import RateLimiter, Window
from app.web.auth import CurrentUserDep
from app.web.i18n import WebText


def require_model_quota(request: Request, principal: CurrentUserDep) -> None:
    """Count one model-backed request for the signed-in person. Raises TooManyRequestsError (429, with how long to
    wait) if their minute's or day's allowance is spent; nothing is counted then."""
    limiter: RateLimiter = request.app.state.model_quota
    refusal = limiter.take(principal.user_id)
    if refusal is None:
        return
    reason = WebText.DAILY_LIMIT if refusal.window is Window.DAY else WebText.TOO_FAST
    raise TooManyRequestsError(translatable(reason), refusal.retry_after_seconds)


# For a route's `dependencies=[MODEL_QUOTA]`: the route runs only if the person's allowance isn't spent.
MODEL_QUOTA = Depends(require_model_quota)
