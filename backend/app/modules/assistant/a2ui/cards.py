"""Ready-made A2UI cards, built by code from tool results (not by the model, for now).

Every value shown comes from the tool's actual result and is placed in a Text: data to show,
never instructions or markup.
"""

import json
import logging
from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import uuid4

from app.modules.assistant.a2ui.models import (
    Card,
    Column,
    Component,
    CreateSurface,
    CreateSurfaceMessage,
    Divider,
    List,
    Row,
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


def _expense_card(prefix: str, title: str, expense: dict[str, Any], footer: str | None = None) -> CreateSurfaceMessage:
    """One expense: a small title with its id, the amount, the merchant, then category and date."""
    body = ["header", "amount", "merchant", "divider", "details"] + (["footer"] if footer else [])
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
    return _surface(prefix, components)


def expense_saved_card(expense: dict[str, Any]) -> CreateSurfaceMessage:
    return _expense_card("expense_saved", "Expense saved", expense)


def expense_updated_card(expense: dict[str, Any]) -> CreateSurfaceMessage:
    return _expense_card("expense_updated", "Expense updated", expense)


def delete_card(result: dict[str, Any]) -> CreateSurfaceMessage:
    """delete_expense has two outcomes; the card must never claim a delete that didn't happen."""
    if result["deleted"]:
        return _expense_card("expense_deleted", "Expense deleted", result["expense"])
    # Without confirmation nothing was deleted (D53): show exactly what would go, and how to confirm.
    footer = 'Nothing is deleted until you reply "yes".'
    return _expense_card("expense_delete_check", "Delete this expense?", result["expense"], footer)


def summary_card(summary: dict[str, Any]) -> CreateSurfaceMessage:
    """One month: the total, the number of expenses, and each category's total, biggest first."""
    month = date.fromisoformat(f"{summary['month']}-01")
    count = summary["expense_count"]
    categories = summary["by_category"]
    body = ["title", "total", "count"] + (["divider", "categories"] if categories else [])
    components: list[Component] = [
        Card(id="root", child="body"),
        Column(id="body", children=body),
        Text(id="title", text=f"Spending in {month:%B %Y}", variant="caption"),
        Text(id="total", text=_money(summary["total"], summary["currency"])),
        Text(id="count", text=f"{count} expense{'' if count == 1 else 's'}", variant="caption"),
    ]
    if categories:
        rows = [f"category_{i}" for i in range(len(categories))]
        components += [Divider(id="divider"), List(id="categories", children=rows)]
        for i, category in enumerate(categories):
            components += [
                Row(id=f"category_{i}", children=[f"category_{i}_name", f"category_{i}_total"], justify="spaceBetween"),
                Text(id=f"category_{i}_name", text=category["category_name"]),
                Text(id=f"category_{i}_total", text=_money(category["total"], summary["currency"])),
            ]
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
