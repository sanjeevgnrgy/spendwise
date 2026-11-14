"""The expenses module's texts for people, in English: their keys, and the source every other language translates.

Part of the expenses module (i18n/). The errors its handlers raise (web/problems.py writes them in the request's
language) and each payment method's label (the assistant's forms; the web app's, through the generated contract).
hi.py translates them; __init__.py registers both catalogs.
"""

from enum import StrEnum

from app.core.i18n import TextValue
from app.modules.expenses.values import PaymentMethod


class ExpenseText(StrEnum):
    """The expenses module's texts, by key."""

    AMOUNT_NOT_POSITIVE = "errors.amountNotPositive"
    CATEGORY_MISSING = "errors.categoryMissing"
    NOT_FOUND = "errors.notFound"
    CHANGED_SINCE_SHOWN = "errors.changedSinceShown"


EN: dict[ExpenseText, TextValue] = {
    ExpenseText.AMOUNT_NOT_POSITIVE: "Amount must be greater than 0",
    ExpenseText.CATEGORY_MISSING: "Category {category_id} does not exist",
    ExpenseText.NOT_FOUND: "Expense {expense_id} not found",
    # A delete that named the version the user saw, after someone changed the expense.
    ExpenseText.CHANGED_SINCE_SHOWN: (
        "Expense {expense_id} has changed since it was shown (version {current}, not {expected}); nothing was deleted."
    ),
}

# How each payment method is written for people. The keys are the methods themselves (a StrEnum).
PAYMENT_METHODS_EN: dict[PaymentMethod, TextValue] = {
    PaymentMethod.CASH: "Cash",
    PaymentMethod.UPI: "UPI",
    PaymentMethod.CARD: "Card",
    PaymentMethod.NETBANKING: "Net banking",
    PaymentMethod.WALLET: "Wallet",
    PaymentMethod.OTHER: "Other",
}
