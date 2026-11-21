"""Which budgets a change pushed into a worse state: the warnings shown when a saved expense crosses 80% or 100%.

The budgets module's domain: a pure function of two statuses (before and after a save), exported through the
package for the MCP tools that save expenses. Moving from on track to near the limit, or into over the limit, is an
alert; staying where it was, or getting better, isn't, so the same warning isn't repeated on every save.
"""

from app.modules.budgets.models import BudgetAlert
from app.modules.budgets.queries.get_budget_status import BudgetLine, BudgetStatus
from app.modules.budgets.values import BudgetState

# How bad each state is: an alert is a move to a higher rank (never to on track).
_RANK = {BudgetState.ON_TRACK: 0, BudgetState.NEAR_LIMIT: 1, BudgetState.OVER_LIMIT: 2}


def _alert(name: str | None, before: BudgetLine | None, after: BudgetLine) -> BudgetAlert | None:
    """An alert if `after` is in a worse state than `before` (no line, or no limit, before counts as on track)."""
    if after.state is None or after.limit is None or after.used_percent is None:
        return None
    was = before.state if before is not None and before.state is not None else BudgetState.ON_TRACK
    if _RANK[after.state] <= _RANK[was]:
        return None
    return BudgetAlert(
        category=name, state=after.state, spent=after.spent, limit=after.limit, used_percent=after.used_percent
    )


def crossed(before: BudgetStatus, after: BudgetStatus) -> list[BudgetAlert]:
    """The budgets that went from `before` to a worse state in `after` (the same month): the categories first, in
    `after`'s order, then the overall budget."""
    earlier = {line.category_id: line for line in before.categories}
    alerts = [_alert(line.category_name, earlier.get(line.category_id), line) for line in after.categories]
    alerts.append(_alert(None, before.overall, after.overall))
    return [alert for alert in alerts if alert is not None]
