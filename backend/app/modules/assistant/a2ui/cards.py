"""Ready-made A2UI cards, built by code from the tools' typed results (not by the model).

Every value shown comes from the tool's actual result and is placed in a Text: data to show,
never instructions or markup.
"""

import logging
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from app.core.money import CURRENCY_SYMBOLS, format_money
from app.core.months import YearMonth
from app.modules.assistant.a2ui.models import (
    ROOT_ID,
    Action,
    ActionName,
    Button,
    Card,
    Chart,
    ChartPoint,
    Column,
    Component,
    CreateSurface,
    CreateSurfaceMessage,
    Divider,
    EventAction,
    List,
    Row,
    ChartType,
    Stat,
    Text,
    Trend,
)
from app.modules.mcp import (
    ExpenseDeleted,
    ExpenseFound,
    ExpenseSaved,
    ExpenseSearch,
    ExpenseUpdated,
    ExpenseView,
    MonthSpending,
    ToolName,
)

logger = logging.getLogger(__name__)

# A list card shows at most this many rows; the rest are summed up in one line.
MAX_LIST_ROWS = 10
# A donut reads best with a few slices, and the theme has five chart colours: the top four
# categories, then everything else together.
DONUT_SLICES = 4
EVERYTHING_ELSE = "Everything else"
SURFACE_ID_LENGTH = 12


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _day(day: date) -> str:
    return f"{day:%d %b %Y}"  # e.g. "13 Nov 2026", like the web app's formatDate


def new_surface_id(prefix: str) -> str:
    # The spec forbids creating the same surface twice, and the same expense can be updated (or a month
    # summed up) more than once in a chat, so every card gets a new surface id.
    return f"{prefix}_{uuid4().hex[:SURFACE_ID_LENGTH]}"


def _surface(surface_id: str, components: list[Component]) -> CreateSurfaceMessage:
    return CreateSurfaceMessage(create_surface=CreateSurface(surface_id=surface_id, components=components))


def expense_ref(expense_id: int) -> str:
    # Shown as "#14" so the user can refer to an expense exactly ("delete #14"); the assistant knows this form.
    return f"#{expense_id}"


def _expense_card(
    surface_id: str, title: str, expense: ExpenseView, footer: str | None = None, extra: list[Component] | None = None
) -> CreateSurfaceMessage:
    """One expense: a small title with its id, the amount, the merchant, then category and date.

    `extra` adds components at the bottom of the card; the first one is the one placed there.
    """
    body = ["header", "amount", "merchant", "divider", "details"] + (["footer"] if footer else [])
    body += [extra[0].id] if extra else []
    components: list[Component] = [
        Card(id=ROOT_ID, child="body"),
        Column(id="body", children=body),
        Row(id="header", children=["title", "reference"], justify="spaceBetween"),
        Text(id="title", text=title, variant="caption"),
        Text(id="reference", text=expense_ref(expense.id), variant="caption"),
        Text(id="amount", text=format_money(expense.amount, expense.currency)),
        Text(id="merchant", text=expense.merchant),
        Divider(id="divider"),
        Row(id="details", children=["category", "date"], justify="spaceBetween"),
        Text(id="category", text=expense.category, variant="caption"),
        Text(id="date", text=_day(expense.spent_on), variant="caption"),
    ]
    if footer:
        components.append(Text(id="footer", text=footer, variant="caption"))
    components += extra or []
    return _surface(surface_id, components)


def _button(id: str, label: str, name: ActionName, user_message: str, primary: bool = False) -> list[Component]:
    """A Button and its label. The click reads as `user_message` in the chat."""
    event = EventAction(name=name, user_message=user_message)
    return [
        Button(id=id, child=f"{id}_label", action=Action(event=event), variant="primary" if primary else None),
        Text(id=f"{id}_label", text=label),
    ]


def approval_card(approval_id: str, expense: ExpenseView) -> CreateSurfaceMessage:
    """What a delete would remove, with Approve and Cancel.

    The surface id IS the approval's id: the server looks the click up by it in its own records, so the
    browser can't change what gets deleted. Nothing is deleted unless Approve is pressed.
    """
    ref = expense_ref(expense.id)
    buttons = [
        Row(id="decision", children=["approve", "cancel"]),
        *_button("approve", "Approve", ActionName.APPROVE_DELETE, f"Approve deleting {ref}", primary=True),
        *_button("cancel", "Cancel", ActionName.CANCEL_DELETE, f"Cancel deleting {ref}"),
    ]
    footer = "Nothing is deleted unless you press Approve."
    return _expense_card(approval_id, "Delete this expense?", expense, footer, buttons)


def _versus(total: Decimal, previous: Decimal, previous_month: date) -> tuple[str, Trend]:
    """'+12% vs October', and which way it went."""
    name = f"{previous_month:%B}"
    if previous == 0:
        return f"Nothing spent in {name}", Trend.FLAT
    if total == previous:
        return f"Same as {name}", Trend.FLAT
    change = (total - previous) / previous * 100
    # Small changes keep a decimal, so ₹10,040 vs ₹10,000 reads "+0.4%", not "Same as".
    text = f"{change:+.1f}%" if abs(change) < 1 else f"{round(change):+d}%"
    return f"{text} vs {name}", Trend.UP if change > 0 else Trend.DOWN


def summary_card(summary: MonthSpending) -> CreateSurfaceMessage:
    """Where the money went in one month: two Stats (vs last month, biggest category) and a donut chart."""
    month = YearMonth.parse(summary.month).first_day()
    previous_month = YearMonth.parse(summary.previous_month.month).first_day()
    change, trend = _versus(summary.total, summary.previous_month.total, previous_month)
    stats = ["stat_total"]
    components: list[Component] = [
        Text(id="title", text=f"Where your money went in {month:%B %Y}", variant="caption"),
        Stat(
            id="stat_total",
            label=f"Spent in {month:%B}",
            value=format_money(summary.total, summary.currency),
            change=change,
            trend=trend,
        ),
    ]
    by_category = summary.by_category  # biggest first
    if by_category:
        top = by_category[0]
        share = round(top.total / summary.total * 100) if summary.total else 0
        stats.append("stat_top")
        components.append(
            Stat(
                id="stat_top",
                label="Biggest category",
                value=top.category_name,
                change=f"{format_money(top.total, summary.currency)} · {share}%",
            )
        )
        slices = [ChartPoint(label=c.category_name, value=float(c.total)) for c in by_category[:DONUT_SLICES]]
        rest = sum((c.total for c in by_category[DONUT_SLICES:]), Decimal(0))
        if rest:
            slices.append(ChartPoint(label=EVERYTHING_ELSE, value=float(rest)))
        components.append(
            Chart(id="chart", chart_type=ChartType.DONUT, data=slices, unit=CURRENCY_SYMBOLS.get(summary.currency))
        )
    count = summary.expense_count
    footer = _plural(count, "expense") if count else f"No expenses in {month:%B %Y}"
    components.append(Text(id="footer", text=footer, variant="caption"))
    body = ["title", "stats"] + (["chart"] if by_category else []) + ["footer"]
    components += [Card(id=ROOT_ID, child="body"), Column(id="body", children=body), Row(id="stats", children=stats)]
    return _surface(new_surface_id("summary"), components)


def expense_list_card(search: ExpenseSearch) -> CreateSurfaceMessage:
    """The expenses a search found, newest first: merchant, id, category and date, and the amount."""
    count = search.count
    shown = search.expenses[:MAX_LIST_ROWS]
    title = "No matching expenses" if count == 0 else f"Found {_plural(count, 'expense')}"
    body = ["title"] + (["expenses"] if shown else []) + (["more"] if count > len(shown) else [])
    components: list[Component] = [
        Card(id=ROOT_ID, child="body"),
        Column(id="body", children=body),
        Text(id="title", text=title, variant="caption"),
    ]
    if shown:
        components.append(List(id="expenses", children=[f"expense_{i}" for i in range(len(shown))]))
        for i, expense in enumerate(shown):
            components += [
                Row(id=f"expense_{i}", children=[f"expense_{i}_info", f"expense_{i}_amount"], justify="spaceBetween"),
                Column(id=f"expense_{i}_info", children=[f"expense_{i}_merchant", f"expense_{i}_meta"]),
                Text(id=f"expense_{i}_merchant", text=expense.merchant),
                Text(
                    id=f"expense_{i}_meta",
                    text=f"{expense_ref(expense.id)} · {expense.category} · {_day(expense.spent_on)}",
                    variant="caption",
                ),
                Text(id=f"expense_{i}_amount", text=format_money(expense.amount, expense.currency)),
            ]
    if count > len(shown):
        components.append(Text(id="more", text=f"Showing the newest {len(shown)} of {count}", variant="caption"))
    return _surface(new_surface_id("expense_list"), components)


def _single(prefix: str, title: str, pick: Callable[[Any], ExpenseView]) -> Callable[[Any], CreateSurfaceMessage]:
    return lambda result: _expense_card(new_surface_id(prefix), title, pick(result))


# Which successful tool results get a card: the result's model, and how to draw it.
_CARDS: dict[ToolName, tuple[type[BaseModel], Callable[[Any], CreateSurfaceMessage]]] = {
    ToolName.ADD_EXPENSE: (ExpenseSaved, _single("expense_saved", "Expense saved", lambda r: r.saved)),
    ToolName.UPDATE_EXPENSE: (ExpenseUpdated, _single("expense_updated", "Expense updated", lambda r: r.updated)),
    ToolName.DELETE_EXPENSE: (ExpenseDeleted, _single("expense_deleted", "Expense deleted", lambda r: r.deleted)),
    ToolName.GET_EXPENSE: (ExpenseFound, _single("expense", "Expense", lambda r: r.expense)),
    ToolName.GET_SUMMARY: (MonthSpending, summary_card),
    ToolName.LIST_EXPENSES: (ExpenseSearch, expense_list_card),
}


def card_for(tool_name: str, data: dict[str, Any] | None) -> CreateSurfaceMessage | None:
    """The card for a successful tool call's structured result, or None if that tool has no card."""
    if tool_name not in _CARDS or data is None:
        return None
    model, build = _CARDS[ToolName(tool_name)]
    try:
        return build(model.model_validate(data))
    except (ValidationError, ArithmeticError) as exc:
        # The card is a bonus on top of the text reply: if the result isn't what we expect, skip it.
        logger.warning("no A2UI card for %s: %s", tool_name, exc)
        return None
