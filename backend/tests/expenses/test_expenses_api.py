"""HTTP tests for the expenses module: real requests through TestClient, in-memory database."""

import pytest


def expense_json(category_id: int, **changes) -> dict:
    """A valid POST /expenses body. Tests override only the fields they care about."""
    body = {
        "amount": "450.50",
        "category_id": category_id,
        "merchant": "Swiggy",
        "spent_on": "2026-11-10",
        "payment_method": "upi",
    }
    return {**body, **changes}


# ---------- create ----------


def test_create_returns_201_and_stores_paise(client, food):
    response = client.post("/expenses", json=expense_json(food.id))

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["amount_minor"] == 45050
    assert body["amount"] == "450.50"
    assert body["currency"] == "INR"


def test_create_with_unknown_category_is_422(client):
    response = client.post("/expenses", json=expense_json(category_id=999))

    assert response.status_code == 422
    assert response.json() == {"detail": "Category 999 does not exist"}


def test_create_with_more_than_two_decimal_places_is_422(client, food):
    response = client.post("/expenses", json=expense_json(food.id, amount="1.005"))

    assert response.status_code == 422


# ---------- read ----------


def test_get_missing_expense_is_404(client):
    response = client.get("/expenses/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Expense 999 not found"}


@pytest.fixture
def three_expenses(client, food, travel):
    # A fixture can use other fixtures: this one builds on client, food and travel.
    client.post("/expenses", json=expense_json(food.id, merchant="Swiggy", spent_on="2026-11-10"))
    client.post("/expenses", json=expense_json(travel.id, merchant="IRCTC", spent_on="2026-11-06"))
    client.post(
        "/expenses", json=expense_json(food.id, merchant="BigBasket", note="Groceries", spent_on="2026-11-01")
    )


@pytest.mark.parametrize(
    ("params", "expected_merchants"),
    [
        ({"merchant": "swiggy"}, ["Swiggy"]),
        ({"search": "grocer"}, ["BigBasket"]),
        ({"start_date": "2026-11-05", "end_date": "2026-11-30"}, ["Swiggy", "IRCTC"]),
        ({}, ["Swiggy", "IRCTC", "BigBasket"]),
    ],
)
def test_list_filters(client, three_expenses, params, expected_merchants):
    # parametrize runs this one test 4 times, once per line above.
    response = client.get("/expenses", params=params)

    assert response.status_code == 200
    # Newest first.
    assert [e["merchant"] for e in response.json()] == expected_merchants


def test_list_filters_by_category(client, three_expenses, travel):
    response = client.get("/expenses", params={"category_id": travel.id})

    assert [e["merchant"] for e in response.json()] == ["IRCTC"]


def test_list_rejects_unknown_filter(client):
    response = client.get("/expenses", params={"catgory_id": 1})

    assert response.status_code == 422


# ---------- update ----------


def test_patch_changes_only_the_fields_sent(client, food):
    created = client.post("/expenses", json=expense_json(food.id, note="Dinner")).json()

    response = client.patch(f"/expenses/{created['id']}", json={"amount": "500.25"})

    assert response.status_code == 200
    updated = response.json()
    assert updated["amount_minor"] == 50025
    assert (updated["merchant"], updated["note"]) == ("Swiggy", "Dinner")


def test_patch_null_note_clears_it_but_null_merchant_is_422(client, food):
    created = client.post("/expenses", json=expense_json(food.id, note="Dinner")).json()

    cleared = client.patch(f"/expenses/{created['id']}", json={"note": None})
    rejected = client.patch(f"/expenses/{created['id']}", json={"merchant": None})

    assert cleared.status_code == 200
    assert cleared.json()["note"] is None
    assert rejected.status_code == 422


def test_patch_missing_expense_is_404(client):
    assert client.patch("/expenses/999", json={"amount": "1"}).status_code == 404


# ---------- delete ----------


def test_delete_returns_204_and_the_expense_is_gone(client, food):
    created = client.post("/expenses", json=expense_json(food.id)).json()

    deleted = client.delete(f"/expenses/{created['id']}")

    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(f"/expenses/{created['id']}").status_code == 404
    assert client.delete(f"/expenses/{created['id']}").status_code == 404


# ---------- summary ----------


def test_summary_totals_one_month_in_one_currency(client, food, travel):
    client.post("/expenses", json=expense_json(food.id, amount="450.50", spent_on="2026-11-10"))
    client.post("/expenses", json=expense_json(food.id, amount="100.00", spent_on="2026-11-30"))
    client.post("/expenses", json=expense_json(travel.id, amount="2340.00", spent_on="2026-11-01"))
    # These two must NOT be counted: a different month, and a different currency.
    client.post("/expenses", json=expense_json(food.id, amount="999.00", spent_on="2026-10-31"))
    client.post("/expenses", json=expense_json(food.id, amount="10.00", currency="USD", spent_on="2026-11-10"))

    response = client.get("/summary", params={"month": "2026-11"})

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_minor"] == 45050 + 10000 + 234000
    assert summary["total"] == "2890.50"
    assert summary["expense_count"] == 3
    # Biggest spend first, with names from the categories module.
    assert [(c["category_name"], c["expense_count"], c["total_minor"]) for c in summary["by_category"]] == [
        ("Travel", 1, 234000),
        ("Food", 2, 55050),
    ]


@pytest.mark.parametrize("month", ["2026-13", "2026-1", "November"])
def test_summary_rejects_a_bad_month(client, month):
    assert client.get("/summary", params={"month": month}).status_code == 422
