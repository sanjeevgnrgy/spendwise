"""The budgets module's texts for people, in every language (budgets module, i18n/), and how an alert is written.

The catalog is registered as this package is imported, after define_catalog has checked every language has every key.
alert_text is the one place a budget alert's wording comes from: the save watcher (the REST routes' notices) and the
assistant's expense card both use it.
"""

from app.core.i18n import Language, define_catalog, text
from app.core.money import BASE_CURRENCY, format_money
from app.modules.budgets.i18n.en import EN, BudgetText
from app.modules.budgets.i18n.hi import HI
from app.modules.budgets.models import BudgetAlert
from app.modules.budgets.values import BudgetState

define_catalog(BudgetText, {Language.EN: EN, Language.HI: HI})


def alert_text(alert: BudgetAlert, language: Language) -> str:
    """One alert as a sentence in `language`: "Food budget: 84.0% used (₹4,200.00 of ₹5,000.00)". Budgets are in INR,
    like every total (D204)."""
    values = {
        "name": alert.category if alert.category is not None else text(language, BudgetText.OVERALL_NAME),
        "spent": format_money(alert.spent, BASE_CURRENCY, language),
        "limit": format_money(alert.limit, BASE_CURRENCY, language),
    }
    if alert.state is BudgetState.OVER_LIMIT:
        return text(language, BudgetText.ALERT_OVER, **values)
    return text(language, BudgetText.ALERT_NEAR, percent=alert.used_percent, **values)


__all__ = ["BudgetText", "alert_text"]
