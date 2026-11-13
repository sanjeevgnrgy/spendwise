# Phase 4: Expenses REST API

**Goal:** full CRUD for expenses over HTTP, a monthly summary, and a categories list. Amounts are typed in
rupees and stored as paise.

## Concepts

**Router → service → repository.** Think of a restaurant:

- The **router** is the waiter. It takes the order (HTTP request), checks it's readable (the schemas), passes
  it to the kitchen, and brings back the plate with the right status code. It never cooks.
- The **service** is the chef. It decides: is the amount above zero? Does that category exist? Every caller
  (the API today, the MCP tools later, the seed script) goes through the chef, so the rules can't be skipped.
- The **repository** is the pantry keeper, the only one who touches the shelves (database).

Each layer can change without the others noticing. Moving to Postgres touches only repositories; adding MCP
tools reuses the services; redesigning URLs touches only routers.

**CRUD** is the four things you do with stored data. Each maps to an HTTP method:

| | HTTP | Route |
|---|---|---|
| **C**reate | `POST` | `POST /expenses` |
| **R**ead | `GET` | `GET /expenses`, `GET /expenses/{id}` |
| **U**pdate | `PATCH` (change some fields) | `PATCH /expenses/{id}` |
| **D**elete | `DELETE` | `DELETE /expenses/{id}` |

**Why input and output models differ.** What a client may *send* and what the server *returns* are different
contracts:

- `ExpenseCreate` (input) has no `id` or `created_at`. The server decides those, and a client must not be able
  to set them.
- `ExpenseCreate` takes `amount` in rupees (`450.50`), because that's what people type.
- `ExpenseRead` (output) adds `id` and `created_at`, and returns both `amount_minor` (the exact stored paise)
  and `amount` (rupees, for display).
- `ExpenseUpdate` (PATCH) makes every field optional, because you send only what changes.

One shared model would let clients write fields they shouldn't, or force them to send values they can't know.

**201 vs 404 vs 422:**

- **201 Created:** the request worked and something new now exists. The response contains it, with its new `id`.
- **404 Not Found:** the thing *in the URL* doesn't exist (`GET /expenses/999999`).
- **422 Unprocessable Content:** the server understood the request but can't accept it. This happens two ways:
  - **Wrong shape**, caught by FastAPI from the schemas: a missing field, `"abc"` as an id, 3 decimal places.
    `detail` is a list naming each problem.
  - **Breaks a business rule**, caught by our service: amount ≤ 0, or a category that doesn't exist.
    `detail` is one sentence.
- Also used: **200 OK** for normal reads and updates, and **204 No Content** for a successful delete, which
  has nothing to return.

## What was built

| File | What changed |
|---|---|
| `core/errors.py` | **New.** `NotFoundError` → 404 and `BusinessRuleError` → 422, mapped in one place |
| `core/db.py` | `SessionDep`: a route parameter that gets a database session per request |
| `modules/expenses/schemas.py` | `ExpenseCreate` (rupees), `ExpenseUpdate`, `ExpenseRead`, `ExpenseFilters`, `MonthlySummary`, `CategoryTotal` |
| `modules/expenses/repository.py` | `add`, `get`, `search`, `update`, `delete`, `totals_by_category` (queries only) |
| `modules/expenses/service.py` | Business rules, plus converting rupees ↔ paise |
| `modules/expenses/router.py` | **New.** The 5 CRUD routes and `GET /summary` |
| `modules/expenses/__init__.py` | Exports every service function and DTO that other modules may use |
| `modules/categories/router.py` | **New.** `GET /categories` |
| `main.py` | Includes both routers and registers the error handlers |
| `seed.py` | Passes amounts in rupees; the service converts them |

**The router is HTTP only** (`modules/expenses/router.py`):

```python
@router.post("/expenses", status_code=201)
def create_expense(body: ExpenseCreate, session: SessionDep) -> ExpenseRead:
    return service.create_expense(session, body)
```

**The service holds the rules** (`modules/expenses/service.py`):

```python
def create_expense(session: Session, data: ExpenseCreate) -> ExpenseRead:
    _check_amount(data.amount)                       # amount > 0, else BusinessRuleError (422)
    _check_category(session, data.category_id)       # via categories.get_category(), else 422
    expense = Expense(amount_minor=rupees_to_paise(data.amount), **data.model_dump(exclude={"amount"}))
    return ExpenseRead.model_validate(repository.add(session, expense))
```

**PATCH changes only what was sent:**

```python
changes = data.model_dump(exclude_unset=True)   # fields the client actually sent
```

`{"note": null}` clears the note. `{"merchant": null}` is a 422, because a merchant can't be empty.

**The summary adds up in the database** (`GROUP BY category_id`). The category names come from the categories
module's public interface, not from a join.

Decisions made in this phase, with reasons: D26–D35 in [decisions.md](../decisions.md).

## The API

| Route | Success | Errors |
|---|---|---|
| `POST /expenses` | 201 + the new expense | 422 (shape, amount ≤ 0, unknown category) |
| `GET /expenses` | 200 + list, newest first | 422 (bad dates, unknown parameter) |
| `GET /expenses/{id}` | 200 + the expense | 404, 422 (id not a number) |
| `PATCH /expenses/{id}` | 200 + the updated expense | 404, 422 |
| `DELETE /expenses/{id}` | 204, no body | 404 |
| `GET /summary?month=YYYY-MM` | 200 + totals | 422 (bad or missing month) |
| `GET /categories` | 200 + list | — |

**Filters for `GET /expenses`** (all optional, combinable):

| Parameter | Matches |
|---|---|
| `start_date`, `end_date` | `spent_on` within the range, both days included |
| `category_id` | that category |
| `merchant` | exact merchant name, any letter case (`swiggy` finds `Swiggy`) |
| `search` | text anywhere in the merchant or note (`grocer` finds the note "Groceries") |

An unknown parameter, such as the typo `catgory_id`, is rejected with 422 instead of being silently ignored.

`GET /summary` also takes `currency` (default `INR`). Totals only make sense within one currency.

## Run it

From the project folder: `.\run.ps1`. No new packages and no database changes; your seeded data still works.
Then open http://127.0.0.1:8000/docs.

## Test it by hand

The easiest way is `/docs`: expand a route, click **Try it out**, then **Execute**. It shows the status code
and the body.

1. **`GET /categories`**: 8 categories. Food is `id` 1.
2. **`POST /expenses`** with:
   ```json
   {"amount": 450.50, "category_id": 1, "merchant": "Chai Point", "spent_on": "2026-11-13", "payment_method": "upi"}
   ```
   You should get **201** with the new `id`, `"amount_minor": 45050`, `"amount": "450.50"`, `"currency": "INR"`
   and a `created_at`.
3. Send the same body with `"amount": -5` → **422** `"Amount must be greater than 0"`.
   With `"category_id": 999` → **422** `"Category 999 does not exist"`.
4. **`GET /expenses/{id}`** with your new id → 200. With `999999` → **404** `"Expense 999999 not found"`.
5. **`GET /expenses`** with `merchant` = `swiggy`, then with `search` = `grocer`, then with a date range.
6. **`PATCH /expenses/{id}`** with `{"amount": 500.25}` → 200. Only `amount` and `amount_minor` change.
7. **`GET /summary`** with `month` = `2026-11`. With the seed data (dated 13 Nov 2026) it looks like this:
   ```json
   {
     "month": "2026-11", "currency": "INR", "expense_count": 8, "total_minor": 826585,
     "by_category": [
       {"category_id": 7, "category_name": "Travel", "expense_count": 1, "total_minor": 234000, "total": "2340.00"},
       {"category_id": 3, "category_name": "Shopping", "expense_count": 1, "total_minor": 189900, "total": "1899.00"},
       {"category_id": 1, "category_name": "Food", "expense_count": 2, "total_minor": 157090, "total": "1570.90"}
     ],
     "total": "8265.85"
   }
   ```
   The list is shortened here; the real one has 7 categories. Two seed expenses fall in October, so they aren't
   counted.
8. **`DELETE /expenses/{id}`** → **204**. Repeat it → **404**.

**What was checked while building it:** 46 automated checks over HTTP against a throwaway database, all
passing. They cover every row of the API table above, including:
- Exact paise for `0.07`; `1.005` rejected.
- Case-insensitive merchant, and `%` searched literally.
- PATCH null handling.
- Summary totals matching the month's expenses.
- `/health` and `/ask` still working.

## Check your understanding

**1. A client sends `POST /expenses` with `"category_id": 42`, and there's no category 42. Why is that 422 and
not 404? What would `GET /expenses/42` return if there's no expense 42?**

<details><summary>Answer</summary>

404 means "the thing **in the URL** doesn't exist". For `POST /expenses`, the URL is fine: the endpoint exists.
The problem is inside the body: it's well-formed JSON but refers to something invalid. That's
"understood but can't be processed", so **422**. `GET /expenses/42` puts the missing thing in the URL, so it's
**404**.
</details>

**2. Why does `ExpenseCreate` have no `id` or `created_at`? Why does `ExpenseRead` return both `amount_minor` and
`amount`, while `ExpenseCreate` takes only `amount`?**

<details><summary>Answer</summary>

The server assigns `id` and `created_at`. If the input model had them, a client could try to choose its own id
or backdate an expense. Input takes rupees because that's what people type. Output returns `amount_minor`
because it's the exact stored value, safe for arithmetic, and `amount` because it's ready to display. `amount`
is computed from `amount_minor`, so the two can never disagree.
</details>

**3. The "amount > 0" check lives in the service, not the router or the schema. Why? What would go wrong if the
MCP tools in a later phase called `repository.add()` directly?**

<details><summary>Answer</summary>

The service is the one place **every** caller goes through: the API, the seed script, and later the MCP tools
and the assistant. A check in the router would protect only HTTP callers. The schema checks shape (is it a
number with ≤ 2 decimals?), while "an expense must be positive" is a business rule, which belongs in the service.
If MCP tools called `repository.add()` directly, they would skip every rule: negative amounts, missing categories,
and rupees never converted to paise. They would also break the module boundary, since the repository isn't part
of the public interface.
</details>
