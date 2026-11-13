"""Service tests for categories: business rules called directly, no HTTP involved."""

import pytest
from pydantic import ValidationError

from app.core.errors import BusinessRuleError
from app.modules import categories


def test_create_category_returns_it_with_an_id(session):
    created = categories.create_category(session, categories.CategoryCreate(name="Health", icon="heart-pulse"))

    assert created.id is not None
    assert (created.name, created.icon) == ("Health", "heart-pulse")


def test_category_names_must_be_unique(session, food):
    with pytest.raises(BusinessRuleError, match="already exists"):
        categories.create_category(session, categories.CategoryCreate(name="Food", icon="other-icon"))


def test_get_category_returns_none_when_missing(session):
    # None (not an error) because other modules use this as a "does it exist?" check.
    assert categories.get_category(session, 999) is None


def test_returned_category_is_read_only(food):
    # Callers get a frozen copy, so they can't change our table through it.
    with pytest.raises(ValidationError):
        food.name = "Changed"
