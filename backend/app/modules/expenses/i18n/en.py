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
    UNSUPPORTED_CURRENCY = "errors.unsupportedCurrency"
    RATES_UNAVAILABLE = "errors.ratesUnavailable"
    RATE_MISSING = "errors.rateMissing"


EN: dict[ExpenseText, TextValue] = {
    ExpenseText.AMOUNT_NOT_POSITIVE: "Amount must be greater than 0",
    ExpenseText.CATEGORY_MISSING: "Category {category_id} does not exist",
    ExpenseText.NOT_FOUND: "Expense {expense_id} not found",
    # A delete that named the version the user saw, after someone changed the expense.
    ExpenseText.CHANGED_SINCE_SHOWN: (
        "Expense {expense_id} has changed since it was shown (version {current}, not {expected}); nothing was deleted."
    ),
    # Saving an amount in another currency (D204): the currency agent has no rate for {currency} (a code, e.g. "XYZ").
    ExpenseText.UNSUPPORTED_CURRENCY: "SpendWise can't convert {currency} to INR yet. Enter the amount in INR instead.",
    # The currency agent can't be asked (or answered something unusable); why goes to the server log (D180).
    ExpenseText.RATES_UNAVAILABLE: (
        "Currency conversion isn't available right now, so an amount in {currency} can't be saved. "
        "Try again in a moment, or enter it in INR."
    ),
    # An amount in {currency} arrived without its rate, or with one for another currency (it changed meanwhile).
    ExpenseText.RATE_MISSING: "The amount in {currency} couldn't be converted to INR. Try saving it again.",
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
