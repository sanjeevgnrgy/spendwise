# Architecture: modular monolith

## The idea

SpendWise's backend is **one FastAPI app, deployed as one unit, with one database**, but divided
inside into **modules by business domain**: expenses, categories, assistant, and later budgets,
splits, receipts, auth and mcp.

Think of an apartment building. Everyone shares the foundation and the plumbing (`core/`).
Each flat (module) has its own locked door. When you need something from a neighbour, you knock
(call their public interface); you don't walk through the wall.

- **Compared with microservices** (separate buildings): one process to run, debug and deploy;
  calls between modules are plain function calls, not network requests.
- **Compared with a "big ball of mud"** (one open-plan floor): the boundaries keep code from
  tangling, so each part can change without breaking the others.
- **Escape hatch:** because modules only meet through their public interfaces, any one of them
  can later be moved out into its own service.

## Layout

```
spendwise/
  backend/
    app/
      main.py           composition root: creates the app, wires in every module
      core/             shared technical code, no business rules
        config.py       settings from .env
        db.py           engine, table creation, get_session
        money.py        rupees <-> paise
        llm.py          ask_gemini()
      modules/
        assistant/      POST /ask
        categories/     Category table + public interface
        expenses/       Expense table + public interface
    seed.py             sample data, using modules' public interfaces
    tests/              (planned) one folder per module + architecture tests
  agents/               (planned) A2A agents: receipt, insights, currency; separate services
  skills/               (planned) Agent Skills
  web/                  (planned) React frontend
```

Modules and folders are added only in the phase that needs them.

## The rules

1. **Split by business domain**, never by technical layer. There is no app-wide `models/` or `routers/` folder.
2. **Each module lives in `backend/app/modules/<name>/`** and owns its tables (`models.py`), `schemas.py`,
   `repository.py`, `service.py` and `router.py`. It only grows the files it actually needs.
3. **Layers inside a module:** router (HTTP only) → service (business rules) → repository (database).
   No business logic in routers.
4. **Modules talk only through public interfaces:** the names exported from `modules/<name>/__init__.py`
   (service functions and DTOs). Never import another module's models, repository or router, and never
   query another module's tables.
5. **Services return DTOs** (frozen Pydantic models such as `CategoryRead`), never table rows.
6. **Links between modules are plain ids** with no database foreign key. They are checked through the
   other module's service.
7. **`core/` never imports from `modules/`.** It holds config, db, money, the LLM client, and later
   logging, errors and events.
8. **`main.py` is the composition root:** the only file that knows every module.
9. **Cross-module reactions** ("an expense was created") will go through a small in-process event bus
   in `core/`, added when first needed.

## Why each module owns its tables

If any module can query any table, that table's columns become a promise to everyone. Renaming a column
or adding a rule then means hunting down every place that reads it. When only `expenses` touches the
expense table, it can rename columns, add indexes or move to another database, and nobody else notices,
as long as its public functions keep working the same way.

That's also why `expense.category_id` has **no foreign key**. A foreign key would tie the two modules'
tables together at the database level. Instead, `expenses.create_expense()` asks
`categories.get_category()` whether the category exists. The trade-off: the database no longer guards
that link, so the service must, and it does.

## Public interfaces today

| Module | Exports (`from app.modules import <name>`) | Used by |
|---|---|---|
| `categories` | `CategoryCreate`, `CategoryRead`, `create_category`, `get_category`, `list_categories` | `expenses`, `seed.py` |
| `expenses` | `ExpenseCreate`, `ExpenseRead`, `PaymentMethod`, `create_expense`, `list_expenses` | `seed.py` |
| `assistant` | nothing yet | `main.py` includes its router |

## How a request flows

`POST /ask`:

```
HTTP request
  -> main.py (app)                      includes the assistant router
  -> modules/assistant/router.py        validates the body (AskRequest), maps GeminiError -> 502
  -> modules/assistant/service.py       answer(prompt): orchestration grows here later
  -> core/llm.py                        ask_gemini(): the only code that talks to Gemini
  -> Gemini API
```

Creating an expense (from `seed.py` today, from a route later):

```
expenses.create_expense(session, ExpenseCreate)
  -> categories.get_category(...)       public interface of another module: "does category 3 exist?"
  -> expenses/repository.add(...)       the only code that writes the expense table
  <- ExpenseRead (frozen copy)
```

## Startup

`main.py` imports `categories` and `expenses` even though it doesn't call them yet. Importing a module
defines its table classes, which registers them with SQLModel. The app's `lifespan` then calls
`create_db_and_tables()`, which creates every registered table that doesn't exist yet. `core` can't do
the importing itself, because core never imports modules.

## Adding a new module

1. Create `backend/app/modules/<name>/` with an `__init__.py` docstring saying what the module is for.
2. Add only the layers you need: `models.py` (tables), `schemas.py` (DTOs), `repository.py` (database
   access), `service.py` (rules, returns DTOs), `router.py` (HTTP).
3. Export the public interface from `__init__.py` with `__all__`.
4. Need another module? Import it as `from app.modules import <other>` and use only its exports.
5. In `main.py`: import the module if it has tables, and `include_router` if it has routes.
6. Document it: phase notes, plus [decisions.md](decisions.md) for any new decision.

## Checking the rules

Until architecture tests are added (planned in `backend/tests/`), these scans from `spendwise/` catch
violations:

```powershell
# Core must never import modules. Expect no output.
Select-String -Path backend\app\core\*.py -Pattern '^\s*(from|import)\s+app\.modules'

# List imports that reach into a module's internals. Each line must be inside that same module's
# folder (e.g. categories/service.py importing app.modules.categories.repository is fine).
Select-String -Path backend\app\modules\*\*.py -Pattern '^\s*(from|import)\s+app\.modules\.'
```
