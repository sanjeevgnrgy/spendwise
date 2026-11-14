"""The expenses module's texts for people, in every language (expenses module, i18n/).

Both catalogs (the module's own texts, and the payment methods' labels) are registered as this package is imported,
after define_catalog has checked every language has every key. The module's __init__.py re-exports ExpenseText and
payment_method_label for other modules.
"""

from app.core.i18n import Language, define_catalog, text
from app.modules.expenses.i18n.en import EN, PAYMENT_METHODS_EN, ExpenseText
from app.modules.expenses.i18n.hi import HI, PAYMENT_METHODS_HI
from app.modules.expenses.values import PaymentMethod

define_catalog(ExpenseText, {Language.EN: EN, Language.HI: HI})
define_catalog(PaymentMethod, {Language.EN: PAYMENT_METHODS_EN, Language.HI: PAYMENT_METHODS_HI})


def payment_method_label(method: PaymentMethod, language: Language) -> str:
    """How `method` is written for people in `language`: "upi" -> "UPI", "netbanking" -> "Net banking"."""
    return text(language, method)


__all__ = ["ExpenseText", "payment_method_label"]
