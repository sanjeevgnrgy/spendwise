"""Service tests for expenses: the business rules, called directly with no HTTP involved.

These would still pass if the routes were deleted, which is the point: the rules live in the
service, so every caller (API, seed script, later the MCP tools) gets them.
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.errors import BusinessRuleError, NotFoundError
from app.modules import expenses


def new_expense(category_id: int, **changes) -> expenses.ExpenseCreate:
    data = {
        "amount": Decimal("450.50"),
        "category_id": category_id,
        "merchant": "Swiggy",
        "spent_on": date(2026, 11, 10),
        "payment_method": "upi",
    }
    return expenses.ExpenseCreate(**{**data, **changes})


def test_amount_is_converted_to_paise(session, food):
    created = expenses.create_expense(session, new_expense(food.id, amount=Decimal("450.50")))

    assert created.amount_minor == 45050
    assert created.amount == Decimal("450.50")


@pytest.mark.parametrize("amount", ["0", "-0.01", "-100"])
def test_amount_must_be_greater_than_zero(session, food, amount):
    with pytest.raises(BusinessRuleError, match="greater than 0"):
        expenses.create_expense(session, new_expense(food.id, amount=Decimal(amount)))


def test_category_must_exist(session):
    with pytest.raises(BusinessRuleError, match="Category 999 does not exist"):
        expenses.create_expense(session, new_expense(category_id=999))


def test_a_rejected_expense_is_not_saved(session, food):
    with pytest.raises(BusinessRuleError):
        expenses.create_expense(session, new_expense(food.id, amount=Decimal("-5")))

    assert expenses.list_expenses(session) == []


def test_update_applies_the_same_rules(session, food):
    created = expenses.create_expense(session, new_expense(food.id))

    with pytest.raises(BusinessRuleError, match="greater than 0"):
        expenses.update_expense(session, created.id, expenses.ExpenseUpdate(amount=Decimal("0")))
    with pytest.raises(BusinessRuleError, match="Category 999"):
        expenses.update_expense(session, created.id, expenses.ExpenseUpdate(category_id=999))

    assert expenses.get_expense(session, created.id).amount_minor == 45050


def test_update_changes_only_the_fields_given(session, food, travel):
    created = expenses.create_expense(session, new_expense(food.id, note="Dinner"))

    updated = expenses.update_expense(session, created.id, expenses.ExpenseUpdate(category_id=travel.id))

    assert updated.category_id == travel.id
    assert (updated.amount_minor, updated.merchant, updated.note) == (45050, "Swiggy", "Dinner")


def test_missing_expense_raises_not_found(session):
    with pytest.raises(NotFoundError):
        expenses.get_expense(session, 999)
    with pytest.raises(NotFoundError):
        expenses.delete_expense(session, 999)


def test_summary_covers_only_the_requested_month_and_currency(session, food):
    expenses.create_expense(session, new_expense(food.id, amount=Decimal("100"), spent_on=date(2026, 12, 31)))
    expenses.create_expense(session, new_expense(food.id, amount=Decimal("200"), spent_on=date(2026, 12, 1)))
    expenses.create_expense(session, new_expense(food.id, amount=Decimal("400"), spent_on=date(2027, 1, 1)))
    expenses.create_expense(session, new_expense(food.id, amount=Decimal("800"), currency="USD", spent_on=date(2026, 12, 5)))

    summary = expenses.monthly_summary(session, 2026, 12)

    assert summary.total_minor == 30000  # 100 + 200 rupees; January and USD left out
    assert summary.expense_count == 2


def test_returned_expense_is_read_only(session, food):
    created = expenses.create_expense(session, new_expense(food.id))

    with pytest.raises(ValidationError):
        created.amount_minor = 1
