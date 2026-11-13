"""Ready-made A2UI cards, built by code from tool results (not by the model, for now).

Every value shown comes from the tool's actual result and is placed in a Text: data to show,
never instructions or markup.
"""

import json
import logging
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from app.modules.assistant.a2ui.models import (
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
    Stat,
    Text,
)

logger = logging.getLogger("spendwise.a2ui")

# A list card shows at most this many rows; the rest are summed up in one line.
MAX_LIST_ROWS = 10


def _money(amount: str, currency: str) -> str:
    return f"₹{amount}" if currency == "INR" else f"{amount} {currency}"


def _day(iso_date: str) -> str:
    return f"{date.fromisoformat(iso_date):%d %b %Y}"  # e.g. "13 Nov 2026"


def _surface(prefix: str, components: list[Component]) -> CreateSurfaceMessage:
    # The spec forbids creating the same surface twice, and the same expense can be updated (or a month
    # summed up) more than once in a chat, so every card gets a new surface id.
    surface = CreateSurface(surface_id=f"{prefix}_{uuid4().hex[:12]}", components=components)
    return CreateSurfaceMessage(create_surface=surface)


def _expense_id(expense: dict[str, Any]) -> str:
    # Shown as "#14" so the user can refer to an expense exactly ("delete #14"); the assistant knows this form.
    return f"#{expense['id']}"


def _expense_card(
    prefix: str,
    title: str,
    expense: dict[str, Any],
    footer: str | None = None,
    extra: list[Component] | None = None,
) -> CreateSurfaceMessage:
    """One expense: a small title with its id, the amount, the merchant, then category and date.

    `extra` adds components at the bottom of the card; the first one is the one placed there.
    """
    body = ["header", "amount", "merchant", "divider", "details"] + (["footer"] if footer else [])
    body += [extra[0].id] if extra else []
    components: list[Component] = [
        Card(id="root", child="body"),
        Column(id="body", children=body),
        Row(id="header", children=["title", "expense_id"], justify="spaceBetween"),
        Text(id="title", text=title, variant="caption"),
        Text(id="expense_id", text=_expense_id(expense), variant="caption"),
        Text(id="amount", text=_money(expense["amount"], expense["currency"])),
        Text(id="merchant", text=expense["merchant"]),
        Divider(id="divider"),
        Row(id="details", children=["category", "date"], justify="spaceBetween"),
        Text(id="category", text=expense["category"], variant="caption"),
        Text(id="date", text=_day(expense["spent_on"]), variant="caption"),
    ]
    if footer:
        components.append(Text(id="footer", text=footer, variant="caption"))
    components += extra or []
    return _surface(prefix, components)


def _button(
    id: str, label: str, name: ActionName, expense_id: int, user_message: str, primary: bool = False
) -> list[Component]:
    """A Button and its label. The click reads as `user_message` in the chat."""
    event = EventAction(name=name, context={"expense_id": expense_id}, user_message=user_message)
    return [
        Button(id=id, child=f"{id}_label", action=Action(event=event), variant="primary" if primary else None),
        Text(id=f"{id}_label", text=label),
    ]


def expense_saved_card(expense: dict[str, Any]) -> CreateSurfaceMessage:
    return _expense_card("expense_saved", "Expense saved", expense)


def expense_updated_card(expense: dict[str, Any]) -> CreateSurfaceMessage:
    return _expense_card("expense_updated", "Expense updated", expense)


def delete_card(result: dict[str, Any]) -> CreateSurfaceMessage:
    """delete_expense has two outcomes; the card must never claim a delete that didn't happen."""
    expense = result["expense"]
    if result["deleted"]:
        return _expense_card("expense_deleted", "Expense deleted", expense)
    # Nothing was deleted yet: show exactly what would go, with the user's two choices. Only the
    # server can turn Approve into a delete (approvals.py); the button just says which card was approved.
    buttons = [
        Row(id="decision", children=["approve", "cancel"]),
        *_button("approve", "Approve", "approve_delete", expense["id"], f"Approve deleting #{expense['id']}", True),
        *_button("cancel", "Cancel", "cancel_delete", expense["id"], f"Cancel deleting #{expense['id']}"),
    ]
    footer = "Nothing is deleted unless you press Approve."
    return _expense_card("expense_delete_check", "Delete this expense?", expense, footer, buttons)


def approval_needed(tool_name: str, result_text: str) -> int | None:
    """The expense id a delete preview is waiting on (its card has Approve/Cancel), or None."""
    if tool_name != "delete_expense":
        return None
    try:
        result = json.loads(result_text)
        return int(result["expense"]["id"]) if result["deleted"] is False else None
    except (ValueError, KeyError, TypeError):
        return None


def _versus(total: Decimal, previous: Decimal, previous_month: date) -> tuple[str, Literal["up", "down", "flat"]]:
    """'+12% vs October', and which way it went."""
    name = f"{previous_month:%B}"
    if previous == 0:
        return f"Nothing spent in {name}", "flat"
    percent = round((total - previous) / previous * 100)
    if percent == 0:
        return f"Same as {name}", "flat"
    return f"{percent:+d}% vs {name}", "up" if percent > 0 else "down"


def summary_card(summary: dict[str, Any]) -> CreateSurfaceMessage:
    """Where the money went in one month: two Stats (vs last month, biggest category) and a donut chart."""
    month = date.fromisoformat(f"{summary['month']}-01")
    currency = summary["currency"]
    total = Decimal(summary["total"])
    count = summary["expense_count"]
    categories = summary["by_category"]  # biggest first

    stats = ["stat_total"]
    components: list[Component] = [
        Text(id="title", text=f"Where your money went in {month:%B %Y}", variant="caption"),
    ]
    previous = summary.get("previous_month")
    change, trend = (
        _versus(total, Decimal(previous["total"]), date.fromisoformat(f"{previous['month']}-01"))
        if previous
        else (None, None)
    )
    components.append(
        Stat(id="stat_total", label=f"Spent in {month:%B}", value=_money(summary["total"], currency), change=change, trend=trend)
    )

    if categories:
        top = categories[0]
        share = round(Decimal(top["total"]) / total * 100) if total else 0
        stats.append("stat_top")
        components.append(
            Stat(id="stat_top", label="Biggest category", value=top["category_name"], change=f"{_money(top['total'], currency)} · {share}%")
        )
        # A donut reads best with a few slices, and the theme has five chart colours: the top four
        # categories, then everything else together.
        slices = [ChartPoint(label=c["category_name"], value=float(c["total"])) for c in categories[:4]]
        rest = sum(Decimal(c["total"]) for c in categories[4:])
        if rest:
            slices.append(ChartPoint(label="Everything else", value=float(rest)))
        components.append(Chart(id="chart", chart_type="donut", data=slices, unit="₹" if currency == "INR" else None))

    footer = f"{count} expense{'' if count == 1 else 's'}" if count else "No expenses yet this month"
    components.append(Text(id="footer", text=footer, variant="caption"))
    body = ["title", "stats"] + (["chart"] if categories else []) + ["footer"]
    components += [Card(id="root", child="body"), Column(id="body", children=body), Row(id="stats", children=stats)]
    return _surface("summary", components)


def expense_list_card(result: dict[str, Any]) -> CreateSurfaceMessage:
    """The expenses a search found, newest first: merchant, id, category and date, and the amount."""
    count = result["count"]
    shown = result["expenses"][:MAX_LIST_ROWS]
    title = "No matching expenses" if count == 0 else f"Found {count} expense{'' if count == 1 else 's'}"
    body = ["title"] + (["expenses"] if shown else []) + (["more"] if count > len(shown) else [])
    components: list[Component] = [
        Card(id="root", child="body"),
        Column(id="body", children=body),
        Text(id="title", text=title, variant="caption"),
    ]
    if shown:
        components.append(List(id="expenses", children=[f"expense_{i}" for i in range(len(shown))]))
        for i, expense in enumerate(shown):
            components += [
                Row(id=f"expense_{i}", children=[f"expense_{i}_info", f"expense_{i}_amount"], justify="spaceBetween"),
                Column(id=f"expense_{i}_info", children=[f"expense_{i}_merchant", f"expense_{i}_meta"]),
                Text(id=f"expense_{i}_merchant", text=expense["merchant"]),
                Text(
                    id=f"expense_{i}_meta",
                    text=f"{_expense_id(expense)} · {expense['category']} · {_day(expense['spent_on'])}",
                    variant="caption",
                ),
                Text(id=f"expense_{i}_amount", text=_money(expense["amount"], expense["currency"])),
            ]
    if count > len(shown):
        components.append(Text(id="more", text=f"Showing the newest {len(shown)} of {count}", variant="caption"))
    return _surface("expense_list", components)


# Which successful tool results get a card, and how each result is read.
_CARDS: dict[str, Callable[[dict[str, Any]], CreateSurfaceMessage]] = {
    "add_expense": lambda result: expense_saved_card(result["saved"]),
    "update_expense": lambda result: expense_updated_card(result["updated"]),
    "delete_expense": delete_card,
    "get_summary": summary_card,
    "list_expenses": expense_list_card,
}


def card_for(tool_name: str, result_text: str) -> CreateSurfaceMessage | None:
    """The A2UI card for a successful tool call, or None if that tool has no card."""
    build = _CARDS.get(tool_name)
    if build is None:
        return None
    try:
        return build(json.loads(result_text))
    except (ValueError, KeyError, TypeError) as exc:  # ValueError includes Pydantic's ValidationError
        # The card is a bonus on top of the text reply: if the result isn't what we expect, skip it.
        logger.warning("no A2UI card for %s: %s", tool_name, exc)
        return None
