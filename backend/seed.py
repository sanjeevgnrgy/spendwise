"""Insert the default categories, and optionally 10 sample expenses for one person. Safe to run more than once.

An entry point (a script), built from the composition root like the web app: it brings the tables up to date,
then sends ordinary commands through the bus, so the sample data passes every rule real data does.

Categories are shared by everyone, so they're always seeded (once). Expenses belong to a person (D190), so the
samples need one: someone who has signed in at least once, named by their email. Run from the project folder:

    .\\.venv\\Scripts\\python.exe backend\\seed.py                              (categories only)
    .\\.venv\\Scripts\\python.exe backend\\seed.py --sample-for you@example.com  (and sample expenses for you)
"""

import argparse
from datetime import date, timedelta
from decimal import Decimal

from app import bootstrap
from app.core.cqrs import MessageBus
from app.core.money import DEFAULT_CURRENCY, format_money, paise_to_rupees
from app.infrastructure import migrations

# Only the modules' contracts, sent through the bus, exactly like any other caller.
from app.modules import accounts, categories, expenses

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


def seed_categories(bus: MessageBus) -> dict[str, int]:
    """The default categories, created in one transaction if there are none yet. Returns every category's id by
    name."""
    if not bus.ask(categories.ListCategories()):
        with bus.unit_of_work():
            for name, icon in DEFAULT_CATEGORIES:
                bus.execute(categories.CreateCategory(name=name, icon=icon))
        print(f"Seeded {len(DEFAULT_CATEGORIES)} categories.")
    else:
        print("Categories already there.")
    return {category.name: category.id for category in bus.ask(categories.ListCategories())}


def owner_for(bus: MessageBus, email: str) -> int | None:
    """The user id of the one person who signed in with `email`, or None (with the reason printed)."""
    found = bus.ask(accounts.FindUsersByEmail(email=email))
    if len(found) == 1:
        return found[0]
    if not found:
        print(f"No one has signed in as {email} yet: sign in once, then run this again.")
    else:
        print(f"Several accounts use {email} (user ids {found}); sample data needs exactly one.")
    return None


def seed_samples(bus: MessageBus, owner_id: int, category_ids: dict[str, int], today: date) -> None:
    """The sample expenses for `owner_id`, in one transaction, unless they already have expenses. Prints them."""
    if bus.ask(expenses.ListExpenses(owner_id=owner_id)).total:
        print("That person already has expenses; no samples added.")
        return
    with bus.unit_of_work():
        for days_ago, rupees, category, merchant, method, note in SAMPLE_EXPENSES:
            new = expenses.NewExpense(
                amount=Decimal(rupees),
                category_id=category_ids[category],
                merchant=merchant,
                note=note,
                spent_on=today - timedelta(days=days_ago),
                payment_method=method,
            )
            bus.execute(expenses.CreateExpense(owner_id=owner_id, expense=new))
    everything = expenses.ExpenseFilters(limit=expenses.MAX_LIST_LIMIT)
    saved = bus.ask(expenses.ListExpenses(owner_id=owner_id, filters=everything)).items
    print(f"Seeded {len(saved)} expenses:")
    for e in saved:
        amount = format_money(e.amount, e.currency)
        print(f"  {e.spent_on}  {amount:>12}  (stored as {e.amount_minor:>6} paise)  {e.merchant}")
    total = sum(e.amount_minor for e in saved)
    print(f"  Total: {format_money(paise_to_rupees(total), DEFAULT_CURRENCY)} (stored as {total} paise)")


def main() -> None:
    """Migrate the database, seed the categories, then the samples for the person named by --sample-for, if any."""
    parser = argparse.ArgumentParser(description="Seed SpendWise's categories and, optionally, sample expenses.")
    parser.add_argument("--sample-for", metavar="EMAIL", help="add 10 sample expenses for the person with this email")
    args = parser.parse_args()
    # The seed may run before the server ever has, so bring the tables up to date first.
    migrations.upgrade_to_latest()
    services = bootstrap.build()
    category_ids = seed_categories(services.bus)
    if args.sample_for:
        owner_id = owner_for(services.bus, args.sample_for)
        if owner_id is not None:
            seed_samples(services.bus, owner_id, category_ids, services.clock.today())


if __name__ == "__main__":
    main()
