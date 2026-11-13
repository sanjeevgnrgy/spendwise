"""The current date and time, as a dependency instead of a global.

Code that asks `date.today()` directly can only ever see the real day, so "this month" can't be
pinned in a check, and every caller silently uses the server's time zone. Handlers get a Clock
instead; the app gives them the system clock, and anything else (a script, a check) can pass its own.
"""

from datetime import UTC, date, datetime
from typing import Protocol


class Clock(Protocol):
    def today(self) -> date: ...

    def now(self) -> datetime: ...


class SystemClock:
    def today(self) -> date:
        # The server's local date. Per-user time zones need users first (the planned auth phase).
        return date.today()

    def now(self) -> datetime:
        # Always UTC for timestamps; showing them in local time is the client's job.
        return datetime.now(UTC)
