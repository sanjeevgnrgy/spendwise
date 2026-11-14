"""Insert default categories and 10 sample expenses. Safe to run more than once.

An entry point (a script), built from the composition root like the web app: it brings the tables up to date,
then sends ordinary commands through the bus, so the sample data passes every rule real data does.

Run from the project folder:  .\\.venv\\Scripts\\python.exe backend\\seed.py
"""

from datetime import timedelta
from decimal import Decimal

from app import bootstrap, migrations
from app.core.money import DEFAULT_CURRENCY, format_money, paise_to_rupees

# Only the modules' contracts, sent through the bus, exactly like any other caller.
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
# Rupees are strings so they become exact Decimals, never floats. The expenses
# handlers convert them to paise, exactly as they do for the API.
SAMPLE_EXPENSES = [
    (1, "450.50", "Food", "Swiggy", expenses.PaymentMethod.UPI, "Dinner"),
    (2, "220.00", "Transport", "Uber", expenses.PaymentMethod.UPI, None),
    (3, "1899.00", "Shopping", "Amazon", expenses.PaymentMethod.CARD, "Headphones"),
    (5, "1250.75", "Bills", "BESCOM", expenses.PaymentMethod.NETBANKING, "Electricity bill"),
    (6, "600.00", "Entertainment", "BookMyShow", expenses.PaymentMethod.CARD, "Movie tickets"),
    (8, "385.20", "Health", "Apollo Pharmacy", expenses.PaymentMethod.CASH, None),
    (10, "2340.00", "Travel", "IRCTC", expenses.PaymentMethod.UPI, "Train to Mysuru"),
    (12, "1120.40", "Food", "BigBasket", expenses.PaymentMethod.UPI, "Groceries"),
    (15, "299.00", "Bills", "Jio", expenses.PaymentMethod.WALLET, "Mobile recharge"),
    (20, "150.00", "Other", "Local tailor", expenses.PaymentMethod.CASH, None),
]


def main() -> None:
    """Migrate the database, then add the sample data in one transaction, unless categories already exist."""
    # The seed may run before the server ever has, so bring the tables up to date first.
    migrations.upgrade_to_latest()
    services = bootstrap.build()
    bus = services.bus

    # Stop if data is already there, so a second run doesn't duplicate everything.
    if bus.ask(categories.ListCategories()):
        print("Already seeded; nothing to do. Delete backend/spendwise.db to start over.")
        return

    today = services.clock.today()
    # One unit of work: everything is saved together, or (if anything fails) nothing is.
    with bus.unit_of_work():
        category_ids = {
            name: bus.execute(categories.CreateCategory(name=name, icon=icon)) for name, icon in DEFAULT_CATEGORIES
        }
        for days_ago, rupees, category, merchant, method, note in SAMPLE_EXPENSES:
            bus.execute(
                expenses.CreateExpense(
                    amount=Decimal(rupees),
                    category_id=category_ids[category],
                    merchant=merchant,
                    note=note,
                    spent_on=today - timedelta(days=days_ago),
                    payment_method=method,
                )
            )

    saved = bus.ask(expenses.ListExpenses(limit=expenses.MAX_LIST_LIMIT)).items
    print(f"Seeded {len(category_ids)} categories and {len(saved)} expenses:")
    for e in saved:
        amount = format_money(e.amount, e.currency)
        print(f"  {e.spent_on}  {amount:>12}  (stored as {e.amount_minor:>6} paise)  {e.merchant}")
    total = sum(e.amount_minor for e in saved)
    print(f"  Total: {format_money(paise_to_rupees(total), DEFAULT_CURRENCY)} (stored as {total} paise)")


if __name__ == "__main__":
    main()
