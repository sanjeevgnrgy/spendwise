"""The budgets module's shared values: the limit's type, the thresholds, and a budget's state.

Part of the module's contract layer. The command and query slices build their messages from these, the rules
(domain/rules.py) apply the thresholds, and __init__.py exports what other modules and the web contract need. This file
imports no other file of the module.
"""

from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import Field

# A monthly limit in rupees (INR, like every total, D204): above zero, at most 12 digits, 2 after the point, like an
# expense's amount. A fraction of a paisa is refused, never rounded away.
BudgetLimit = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2, examples=["8000.00"])]

# A budget is "near its limit" from this share of it on, and "over" once spending passes it. The assistant warns when
# a saved expense crosses either line (Phase 27, part 2).
NEAR_LIMIT_PERCENT = 80
FULL_PERCENT = 100


# Where a month's spending stands against a budget. The value is what the API sends; the web app shows a colour and a
# text for each.
class BudgetState(StrEnum):
    # Below NEAR_LIMIT_PERCENT of the limit.
    ON_TRACK = "on_track"
    # From NEAR_LIMIT_PERCENT up to the limit itself.
    NEAR_LIMIT = "near_limit"
    # More than the limit.
    OVER_LIMIT = "over_limit"
