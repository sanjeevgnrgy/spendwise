"""The budgets module's texts for people, in English: their keys, and the source every other language translates.

Part of the budgets module (i18n/): the errors its handlers raise (a problem's detail, in the request's language).
hi.py translates them; __init__.py registers the catalog.
"""

from enum import StrEnum

from app.core.i18n import TextValue


class BudgetText(StrEnum):
    """The budgets module's texts, by key."""

    CATEGORY_MISSING = "errors.categoryMissing"
    NO_OVERALL_BUDGET = "errors.noOverallBudget"
    NO_CATEGORY_BUDGET = "errors.noCategoryBudget"


EN: dict[BudgetText, TextValue] = {
    BudgetText.CATEGORY_MISSING: "Category {category_id} does not exist",
    # Removing a budget that isn't there (never set, or already removed).
    BudgetText.NO_OVERALL_BUDGET: "You have no overall monthly budget.",
    BudgetText.NO_CATEGORY_BUDGET: "You have no budget for category {category_id}.",
}
