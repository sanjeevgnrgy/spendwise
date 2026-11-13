"""Insert default categories and 10 sample expenses. Safe to run more than once.

Run from the spendwise/ folder:  .\\.venv\\Scripts\\python.exe backend\\seed.py
"""

from datetime import date, timedelta

from sqlmodel import Session

from app.core.db import create_db_and_tables, engine
from app.core.money import paise_to_rupees, rupees_to_paise

# Only the modules' public interfaces, exactly like any other caller would use them.
from app.modules import categories, expenses

DEFAULT_CATEGORIES = [
    ("Food", "utensils"),
    ("Transport", "bus"),
    ("Shopping", "shopping-bag"),
    ("Bills", "receipt"),
    ("Entertainment", "film"),
    ("Health", "heart-pulse"),
    ("Travel", "plane"),
    ("Other", "tag"),
]

# (days ago, rupees, category, merchant, payment method, note)
# Rupees are strings so they go through Decimal, never through a float.
SAMPLE_EXPENSES = [
    (1, "450.50", "Food", "Swiggy", "upi", "Dinner"),
    (2, "220.00", "Transport", "Uber", "upi", None),
    (3, "1899.00", "Shopping", "Amazon", "card", "Headphones"),
    (5, "1250.75", "Bills", "BESCOM", "netbanking", "Electricity bill"),
    (6, "600.00", "Entertainment", "BookMyShow", "card", "Movie tickets"),
    (8, "385.20", "Health", "Apollo Pharmacy", "cash", None),
    (10, "2340.00", "Travel", "IRCTC", "upi", "Train to Mysuru"),
    (12, "1120.40", "Food", "BigBasket", "upi", "Groceries"),
    (15, "299.00", "Bills", "Jio", "wallet", "Mobile recharge"),
    (20, "150.00", "Other", "Local tailor", "cash", None),
]


def main() -> None:
    # The seed may run before the server ever has, so make sure the tables exist.
    create_db_and_tables()

    with Session(engine) as session:
        # Stop if data is already there, so a second run doesn't duplicate everything.
        if categories.list_categories(session):
            print("Already seeded; nothing to do. Delete backend/spendwise.db to start over.")
            return

        category_ids = {}
        for name, icon in DEFAULT_CATEGORIES:
            created = categories.create_category(session, categories.CategoryCreate(name=name, icon=icon))
            category_ids[name] = created.id

        today = date.today()
        for days_ago, rupees, category, merchant, method, note in SAMPLE_EXPENSES:
            expenses.create_expense(
                session,
                expenses.ExpenseCreate(
                    amount_minor=rupees_to_paise(rupees),
                    category_id=category_ids[category],
                    merchant=merchant,
                    note=note,
                    spent_on=today - timedelta(days=days_ago),
                    payment_method=method,
                ),
            )

        saved = expenses.list_expenses(session)
        print(f"Seeded {len(category_ids)} categories and {len(saved)} expenses:")
        for e in saved:
            print(f"  {e.spent_on}  {e.currency} {paise_to_rupees(e.amount_minor):>8}  "
                  f"(stored as {e.amount_minor:>6} paise)  {e.merchant}")
        total = sum(e.amount_minor for e in saved)
        print(f"  Total: INR {paise_to_rupees(total)} (stored as {total} paise)")


if __name__ == "__main__":
    main()
