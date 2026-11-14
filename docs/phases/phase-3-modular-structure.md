# Phase 3: Modular structure and data model

> **Later changes:**
> **Refactor (after Phase 18):** modules now speak in commands and queries through a bus (CQRS). Files were renamed by
> role (`models.py` → `tables.py`, `schemas.py` → `contracts.py`, `service.py` → `commands.py` / `queries.py`,
> `router.py` → `api.py`); `bootstrap.py` is the composition root; Alembic migrations create the tables instead of
> `create_all`. See [refactor-architecture.md](refactor-architecture.md).

**Goal:** restructure the backend into a modular monolith, add a database with `categories` and `expenses`
modules, money helpers, and a seed script, keeping `/health` and `/ask` working.

> **Later changes:** in Phase 4, `ExpenseCreate` takes `amount` in rupees instead of `amount_minor`, and the
> service does the conversion. `main.py` now imports each module through its router. The duplicate-category
> error became `BusinessRuleError`. After Phase 4, the project moved from `spendwise/` to the repo root, so
> "from `spendwise\`" below means the project folder. This page records Phase 3 as it was built.

## Design

- **Modular monolith:** one app, deployed as one unit, with one database, divided inside into modules by
  business domain. Like an apartment building: shared foundation and plumbing (`core/`), separate flats
  (modules) with locked doors. To get something from a neighbour you knock (call their public interface in
  `__init__.py`); you don't walk through the wall. It's as simple to run as one app, stays organised like
  separate services, and any module can later be moved out into its own service.
  Full rules: [architecture.md](../architecture.md).
- **Why each module owns its tables:** if any module can query any table, its columns become a promise to
  everyone. When only `expenses` touches the expense table, it can change it freely as long as its public
  functions keep working. That's why `expense.category_id` has **no foreign key**; the expenses service asks
  `categories.get_category()` instead.
- **Why 450.50 rupees is stored as 45050 paise:** floats are binary and can't hold most decimal fractions exactly
  (`0.1 + 0.2 = 0.30000000000000004`). Over thousands of additions those errors become paise that appear or
  vanish. Whole numbers are exact, so we count the smallest unit, like a cashier counting coins. Conversions
  happen only in `core/money.py`, using `Decimal`.
- **New tools:**
  - **pydantic-settings** reads `.env` into a typed `Settings` object.
  - **SQLModel** defines tables as Python classes.
  - A **Session** is one conversation with the database: open it, use it, close it.
  - FastAPI's **lifespan** runs code once at startup.

## What was built

```
backend/
  app/
    main.py                 composition root: lifespan creates tables, includes routers
    core/
      config.py             Settings from .env (pydantic-settings, SecretStr key)
      db.py                 engine from DATABASE_URL, create_db_and_tables(), get_session()
      money.py              rupees_to_paise(), paise_to_rupees()
      llm.py                ask_gemini() (moved here)
    modules/
      assistant/            POST /ask: router, schemas, service
      categories/           models, schemas, repository, service, public __init__
      expenses/             models, schemas, repository, service, public __init__
  seed.py                   8 default categories + 10 sample expenses
```

**Crossing a module boundary the right way** (`modules/expenses/service.py`):

```python
from app.modules import categories          # the public interface, nothing deeper

def create_expense(session: Session, data: ExpenseCreate) -> ExpenseRead:
    # Ask the categories module whether the category exists, instead of reading its table.
    if categories.get_category(session, data.category_id) is None:
        raise ValueError(f"Category {data.category_id} does not exist")
    expense = repository.add(session, Expense(**data.model_dump()))
    return ExpenseRead.model_validate(expense)
```

**Money** (`core/money.py`):

```python
def rupees_to_paise(rupees: Decimal | int | str) -> int:
    # Decimal, never float: floats can't hold most decimal fractions exactly (0.1 + 0.2 != 0.3).
    paise = Decimal(str(rupees)) * PAISE_PER_RUPEE
    # Refuse fractions of a paisa rather than silently rounding money away.
    if paise != paise.to_integral_value():
        raise ValueError(f"{rupees} rupees has more than 2 decimal places")
    return int(paise)
```

**Tables:**
- `Category`: `id`, `name` (unique), `icon`.
- `Expense`: `id`, `amount_minor` (paise), `currency` (default `INR`), `category_id` (no FK), `merchant`,
  `note`, `spent_on`, `payment_method`, `created_at` (UTC).

Choices made in this phase, with reasons, are D12–D23 in [decisions.md](../decisions.md): no foreign keys,
frozen DTOs, `SecretStr`, a re-runnable seed, icon names, no migrations yet, `/hello` removed, and more.

## Run it

1. Stop any old server (Ctrl+C). The start command changed to `app.main:app --app-dir backend`.
2. From `spendwise\`: `.\run.ps1`. It installs SQLModel and pydantic-settings first, because `requirements.txt` changed.
3. In a second terminal: `.\.venv\Scripts\python.exe backend\seed.py`.

## Verify it by hand

**Seed on a fresh database** (dates are relative to today):

```
Seeded 8 categories and 10 expenses:
  2026-11-12  INR   450.50  (stored as  45050 paise)  Swiggy
  2026-11-11  INR   220.00  (stored as  22000 paise)  Uber
  ...
  2026-10-24  INR   150.00  (stored as  15000 paise)  Local tailor
  Total: INR 8714.85 (stored as 871485 paise)
```

Running it again prints `Already seeded; nothing to do. Delete backend/spendwise.db to start over.`

**Server:**
- `/health` → `{"status":"ok"}`.
- `/docs` → `/health`, plus **POST /ask** under "assistant". There are no expense routes yet.
- `/ask` works as in Phase 2.

**What was checked while building it:**
- `/health` returns ok, and `/ask` gives 422 for an empty prompt and 502 for a wrong key.
- Starting on an empty database creates both tables.
- The seed works, and a second run doesn't duplicate anything.
- Money:
  - `"450.50"` ↔ `45050`.
  - Every amount from 0 to 100000 paise survives a round trip to rupees and back.
  - `1.005` rupees and the float `0.1 + 0.2` are rejected.
- Validation: an unknown category, a negative amount, an unknown payment method and a duplicate category
  name are rejected.
- DTOs are read-only. There's no foreign key on `expense`, and no expense points at a missing category.
- An import scan confirms that `core/` never imports a module, and that the only cross-module import is
  `from app.modules import categories`.

## Design questions

**1. The expenses module needs to know whether category 3 exists. What may it import? What would go wrong
over time if it ran `select(Category)` itself?**

<details><summary>Answer</summary>

Only the categories module's public interface: `from app.modules import categories`, then
`categories.get_category(session, 3)`. Querying `Category` directly would couple expenses to the categories
table's columns and bypass the categories module's own rules. Categories could then no longer rename a column,
add a rule (e.g. "archived categories don't count"), or move to its own database without breaking expenses.
That hidden dependency is exactly what module boundaries prevent.
</details>

**2. Why does `rupees_to_paise(0.1 + 0.2)` raise an error, while `rupees_to_paise("0.30")` returns `30`?**

<details><summary>Answer</summary>

`0.1 + 0.2` is the float `0.30000000000000004`. Converted to `Decimal` and multiplied by 100, that's
`30.000000000000004` paise, which isn't a whole number, so the function refuses it rather than silently rounding.
The string `"0.30"` becomes exactly `Decimal("0.30")`, which is exactly 30 paise.
</details>

**3. `main.py` imports `categories` and `expenses` but never uses a name from them. If you deleted that line
and started on a new, empty database, what would happen?**

<details><summary>Answer</summary>

The server would start and `/health` would work, but **no tables would be created**. Table classes register
themselves with SQLModel only when their module is imported, and `create_db_and_tables()` creates only
registered tables. The first query against them would then fail with "no such table". (`seed.py` would still
work on its own, because it imports both modules itself.)
</details>
