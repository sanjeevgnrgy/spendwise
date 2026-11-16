"""Per-person allowances: how many times something may be done in a minute and in a day (core layer).

Used to limit the requests that call the language model, each of which spends quota (D194). The composition root
builds one RateLimiter with the settings' limits and the app's clock; web/rate_limits.py asks it before each such
request and turns a refusal into a 429. Counted in memory, so each server process counts on its own (one process
today; several would need a shared store such as Redis).

Fixed windows: the minute that's running and the day that's running (UTC). Simple and small (one entry per person);
at a window's edge a burst of up to twice a minute's allowance can pass, which is acceptable for a quota guard.
"""

import math
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from app.core.clock import Clock

ONE_MINUTE = timedelta(minutes=1)
ONE_DAY = timedelta(days=1)


class Window(StrEnum):
    """Which allowance ran out."""

    MINUTE = "minute"
    DAY = "day"


@dataclass(frozen=True)
class Refusal:
    """Why a use was refused: which allowance ran out, and how many seconds until it starts again."""

    window: Window
    retry_after_seconds: int


@dataclass
class _Usage:
    """One person's count in the current minute and the current day."""

    minute: datetime
    in_minute: int
    day: date
    in_day: int


class RateLimiter:
    """Counts uses per key (a person's user id) against a minute's and a day's allowance. Safe across threads."""

    def __init__(self, clock: Clock, per_minute: int, per_day: int) -> None:
        """Allow `per_minute` uses in any one minute and `per_day` in any one day (UTC), by `clock`'s time."""
        self._clock = clock
        self._per_minute = per_minute
        self._per_day = per_day
        self._usage: dict[int, _Usage] = {}
        # Routes run in worker threads: two requests from one person must not both read the same count.
        self._lock = threading.Lock()

    def take(self, key: int) -> Refusal | None:
        """Count one use for `key` and return None; or, if an allowance is spent, count nothing and return why."""
        now = self._clock.now()
        minute = now.replace(second=0, microsecond=0)
        with self._lock:
            usage = self._usage.get(key)
            if usage is None or usage.day != now.date():
                usage = _Usage(minute=minute, in_minute=0, day=now.date(), in_day=0)
            elif usage.minute != minute:
                usage = _Usage(minute=minute, in_minute=0, day=usage.day, in_day=usage.in_day)
            if usage.in_day >= self._per_day:
                midnight = datetime.combine(usage.day, datetime.min.time(), now.tzinfo) + ONE_DAY
                return Refusal(Window.DAY, _seconds_until(now, midnight))
            if usage.in_minute >= self._per_minute:
                return Refusal(Window.MINUTE, _seconds_until(now, minute + ONE_MINUTE))
            usage.in_minute += 1
            usage.in_day += 1
            self._usage[key] = usage
            return None


def _seconds_until(now: datetime, moment: datetime) -> int:
    """Whole seconds from `now` until `moment`, rounded up, and at least 1 (a Retry-After of 0 invites a hot loop)."""
    return max(1, math.ceil((moment - now).total_seconds()))
