"""The budget card, and the budget alerts shown under a saved expense (Phase 27, D211).

Presentation layer. cards.card_for draws budget_card, in the request's language, for a successful get_budgets or
set_budget result (the budgets module's BudgetStatus): the overall budget as a Stat, then each category that has a
limit, with its share used and its state, and how much of the month has gone by. alert_texts writes the alerts that
add_expense and update_expense return, for the expense card's footer. Every value shown comes from the tool's result
and is placed in a Text or a Stat: data to show, never instructions or markup.
"""

from functools import partial

from app.core.i18n import Language, format_month, text
from app.core.money import format_money
from app.core.months import YearMonth
from app.modules import budgets
from app.modules.assistant.a2ui.models import (
    ROOT_ID,
    Card,
    Column,
    Component,
    CreateSurfaceMessage,
    List,
    Row,
    Stat,
    Text,
)
from app.modules.assistant.a2ui.parts import new_surface_id, surface
from app.modules.assistant.i18n import ChatText

# How each state reads in a sentence ("84.0% used · near the limit").
_STATES = {
    budgets.BudgetState.ON_TRACK: ChatText.BUDGET_STATE_ON_TRACK,
    budgets.BudgetState.NEAR_LIMIT: ChatText.BUDGET_STATE_NEAR_LIMIT,
    budgets.BudgetState.OVER_LIMIT: ChatText.BUDGET_STATE_OVER_LIMIT,
}


def _overall(status: budgets.BudgetStatus, language: Language) -> Component:
    """The overall budget as a Stat: "₹5,700.50 of ₹10,000.00", with its share used or how much over."""
    t = partial(text, language)  # t(key, **values): a text in the request's language
    money = partial(format_money, currency=status.currency, language=language)
    line = status.overall
    label = t(ChatText.BUDGET_OVERALL)
    if line.limit is None or line.remaining is None or line.used_percent is None or line.state is None:
        return Stat(id="overall", label=label, value=money(line.spent), change=t(ChatText.BUDGET_NO_OVERALL))
    if line.state is budgets.BudgetState.OVER_LIMIT:
        change = t(ChatText.BUDGET_OVER_BY, amount=money(-line.remaining))
    else:
        change = t(ChatText.BUDGET_USED, percent=line.used_percent, state=t(_STATES[line.state]))
    value = t(ChatText.BUDGET_SPENT_OF, spent=money(line.spent), limit=money(line.limit))
    return Stat(id="overall", label=label, value=value, change=change)


def _categories(status: budgets.BudgetStatus, language: Language) -> list[Component]:
    """A row per category with a limit: its name and share used, and "₹4,200 of ₹5,000". Empty if none has one."""
    t = partial(text, language)  # t(key, **values): a text in the request's language
    money = partial(format_money, currency=status.currency, language=language)
    # Each category with a limit, its limit and state already known not to be None.
    budgeted = [(line, line.limit, line.state) for line in status.categories if line.limit is not None and line.state]
    if not budgeted:
        return []
    components: list[Component] = [List(id="categories", children=[f"cat_{i}" for i in range(len(budgeted))])]
    for i, (line, limit, state) in enumerate(budgeted):
        used = t(ChatText.BUDGET_USED, percent=line.used_percent, state=t(_STATES[state]))
        amounts = t(ChatText.BUDGET_SPENT_OF, spent=money(line.spent), limit=money(limit))
        components += [
            Row(id=f"cat_{i}", children=[f"cat_{i}_info", f"cat_{i}_amount"], justify="spaceBetween"),
            Column(id=f"cat_{i}_info", children=[f"cat_{i}_name", f"cat_{i}_used"]),
            Text(id=f"cat_{i}_name", text=line.category_name),
            Text(id=f"cat_{i}_used", text=used, variant="caption"),
            Text(id=f"cat_{i}_amount", text=amounts),
        ]
    return components


def budget_card(status: budgets.BudgetStatus, language: Language) -> CreateSurfaceMessage:
    """The month's budgets as a card, in `language`; with no limits at all, a line saying how to set one."""
    t = partial(text, language)  # t(key, **values): a text in the request's language
    month = format_month(YearMonth.parse(status.month).first_day(), language)
    categories = _categories(status, language)
    has_any = bool(categories) or status.overall.limit is not None
    footer = t(ChatText.BUDGET_ELAPSED, percent=status.month_elapsed_percent) if has_any else t(ChatText.BUDGETS_NONE)
    body = ["title", "overall"] + (["categories"] if categories else []) + ["footer"]
    components: list[Component] = [
        Card(id=ROOT_ID, child="body"),
        Column(id="body", children=body),
        Text(id="title", text=t(ChatText.BUDGETS_TITLE, month=month), variant="caption"),
        _overall(status, language),
        *categories,
        Text(id="footer", text=footer, variant="caption"),
    ]
    return surface(new_surface_id("budgets"), components)


def alert_texts(alerts: list[budgets.BudgetAlert], language: Language) -> list[str]:
    """Each alert as a sentence for the expense card, worded by the budgets module (budgets.alert_text)."""
    return [budgets.alert_text(alert, language) for alert in alerts]
