"""Ready-made A2UI cards, built by code from the tools' typed results (not by the model), in the request's language.

Presentation layer. The AG-UI adapter (api/agui_stream.py) asks card_for() for a card after each
successful tool call, and approval_card() for a delete waiting for Approve. The month's summary card is in
summary_card.py; parts.py has what every card is built with (surface ids, "#14").

Every value shown comes from the tool's actual result and is placed in a Text: data to show,
never instructions or markup.
"""

import logging
from collections.abc import Callable
from functools import partial
from typing import Any

from pydantic import BaseModel, ValidationError

from app.core.i18n import Language, format_day, text
from app.core.money import format_money
from app.modules.assistant.a2ui.models import (
    ROOT_ID,
    Action,
    ActionName,
    Button,
    Card,
    Column,
    Component,
    CreateSurfaceMessage,
    Divider,
    EventAction,
    List,
    Row,
    Text,
)
from app.modules.assistant.a2ui.parts import expense_ref, new_surface_id, surface
from app.modules.assistant.a2ui.summary_card import summary_card
from app.modules.assistant.i18n import ChatText
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

# Draws one tool's typed result as a card, in the given language.
CardBuilder = Callable[[Any, Language], CreateSurfaceMessage]


def _expense_card(
    surface_id: str,
    title: str,
    expense: ExpenseView,
    language: Language,
    footer: str | None = None,
    extra: list[Component] | None = None,
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
        Text(id="amount", text=format_money(expense.amount, expense.currency, language)),
        Text(id="merchant", text=expense.merchant),
        Divider(id="divider"),
        Row(id="details", children=["category", "date"], justify="spaceBetween"),
        Text(id="category", text=expense.category, variant="caption"),
        Text(id="date", text=format_day(expense.spent_on, language), variant="caption"),
    ]
    if footer:
        components.append(Text(id="footer", text=footer, variant="caption"))
    components += extra or []
    return surface(surface_id, components)


def _button(id: str, label: str, name: ActionName, user_message: str, primary: bool = False) -> list[Component]:
    """A Button and its label. The click reads as `user_message` in the chat."""
    event = EventAction(name=name, user_message=user_message)
    return [
        Button(id=id, child=f"{id}_label", action=Action(event=event), variant="primary" if primary else None),
        Text(id=f"{id}_label", text=label),
    ]


def approval_card(approval_id: str, expense: ExpenseView, language: Language) -> CreateSurfaceMessage:
    """What a delete would remove, with Approve and Cancel, in `language`.

    The surface id IS the approval's id: the server looks the click up by it in its own records, so the
    browser can't change what gets deleted. Nothing is deleted unless Approve is pressed. The buttons'
    labels and messages are only shown: the click is recognised by its action's name, never by its words.
    """
    t = partial(text, language)  # t(key, **values): a text in the request's language
    ref = expense_ref(expense.id)
    approve = t(ChatText.DELETE_APPROVE_MESSAGE, ref=ref)
    cancel = t(ChatText.DELETE_CANCEL_MESSAGE, ref=ref)
    buttons = [
        Row(id="decision", children=["approve", "cancel"]),
        *_button("approve", t(ChatText.DELETE_APPROVE), ActionName.APPROVE_DELETE, approve, primary=True),
        *_button("cancel", t(ChatText.DELETE_CANCEL), ActionName.CANCEL_DELETE, cancel),
    ]
    footer = t(ChatText.DELETE_FOOTER)
    return _expense_card(approval_id, t(ChatText.DELETE_TITLE), expense, language, footer, buttons)


def expense_list_card(search: ExpenseSearch, language: Language) -> CreateSurfaceMessage:
    """The expenses a search found, newest first: merchant, id, category and date, and the amount."""
    t = partial(text, language)  # t(key, **values): a text in the request's language
    count = search.count
    shown = search.expenses[:MAX_LIST_ROWS]
    title = t(ChatText.LIST_NONE) if count == 0 else t(ChatText.LIST_FOUND, count=count)
    body = ["title"] + (["expenses"] if shown else []) + (["more"] if count > len(shown) else [])
    components: list[Component] = [
        Card(id=ROOT_ID, child="body"),
        Column(id="body", children=body),
        Text(id="title", text=title, variant="caption"),
    ]
    if shown:
        components.append(List(id="expenses", children=[f"expense_{i}" for i in range(len(shown))]))
        for i, expense in enumerate(shown):
            ref, day = expense_ref(expense.id), format_day(expense.spent_on, language)
            details = t(ChatText.LIST_ROW_DETAILS, ref=ref, category=expense.category, date=day)
            components += [
                Row(id=f"expense_{i}", children=[f"expense_{i}_info", f"expense_{i}_amount"], justify="spaceBetween"),
                Column(id=f"expense_{i}_info", children=[f"expense_{i}_merchant", f"expense_{i}_meta"]),
                Text(id=f"expense_{i}_merchant", text=expense.merchant),
                Text(id=f"expense_{i}_meta", text=details, variant="caption"),
                Text(id=f"expense_{i}_amount", text=format_money(expense.amount, expense.currency, language)),
            ]
    if count > len(shown):
        more = t(ChatText.LIST_MORE, shown=len(shown), total=count)
        components.append(Text(id="more", text=more, variant="caption"))
    return surface(new_surface_id("expense_list"), components)


def _single(prefix: str, title: ChatText, pick: Callable[[Any], ExpenseView]) -> CardBuilder:
    """A card builder for a result holding one expense: `pick` finds it, the card shows it under `title`."""
    return lambda result, language: _expense_card(new_surface_id(prefix), text(language, title), pick(result), language)


# Which successful tool results get a card: the result's model, and how to draw it.
_CARDS: dict[ToolName, tuple[type[BaseModel], CardBuilder]] = {
    ToolName.ADD_EXPENSE: (ExpenseSaved, _single("expense_saved", ChatText.EXPENSE_SAVED, lambda r: r.saved)),
    ToolName.UPDATE_EXPENSE: (
        ExpenseUpdated,
        _single("expense_updated", ChatText.EXPENSE_UPDATED, lambda r: r.updated),
    ),
    ToolName.DELETE_EXPENSE: (
        ExpenseDeleted,
        _single("expense_deleted", ChatText.EXPENSE_DELETED, lambda r: r.deleted),
    ),
    ToolName.GET_EXPENSE: (ExpenseFound, _single("expense", ChatText.EXPENSE_FOUND, lambda r: r.expense)),
    ToolName.GET_SUMMARY: (MonthSpending, summary_card),
    ToolName.LIST_EXPENSES: (ExpenseSearch, expense_list_card),
}


def card_for(tool_name: str, data: dict[str, Any] | None, language: Language) -> CreateSurfaceMessage | None:
    """The card for a successful tool call's structured result, in `language`; None if that tool has no card."""
    if tool_name not in _CARDS or data is None:
        return None
    model, build = _CARDS[ToolName(tool_name)]
    try:
        return build(model.model_validate(data), language)
    except (ValidationError, ArithmeticError, KeyError, ValueError) as exc:
        # The card is a bonus on top of the text reply: if the result isn't what we expect, or a text can't be
        # written (a catalog or formatting mistake), skip it rather than fail a run whose tool already ran.
        logger.warning("no A2UI card for %s: %s", tool_name, exc)
        return None
