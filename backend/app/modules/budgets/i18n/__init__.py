"""The budgets module's texts for people, in every language (budgets module, i18n/).

The catalog is registered as this package is imported, after define_catalog has checked every language has every key.
"""

from app.core.i18n import Language, define_catalog
from app.modules.budgets.i18n.en import EN, BudgetText
from app.modules.budgets.i18n.hi import HI

define_catalog(BudgetText, {Language.EN: EN, Language.HI: HI})

__all__ = ["BudgetText"]
