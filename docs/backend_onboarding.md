# Backend Onboarding

A working guide to the backend (`backend/`): how it's put together, the patterns you'll meet, and step-by-step
recipes for the changes you'll make most. Read [architecture.md](architecture.md) first for the rules; this page is
the "how".

## The mental model in five lines

1. A **module** per business domain (`categories`, `expenses`, `conversations`, `assistant`) owns its tables.
2. Every operation is a **command** (changes data, returns at most an id) or a **query** (reads), a small frozen
   Pydantic model with **one handler**, both in one file (a vertical slice).
3. Everything goes through the **bus**: `bus.execute(command)`, `bus.ask(query)`. The bus is the unit of work: it
   opens the session, commits once, rolls back on error.
4. **Adapters** translate the outside world into messages: REST routes (`api.py`), the MCP server, the AG-UI adapter.
5. **`bootstrap.py`** wires it all together. Modules never import each other's files, only each other's package.

## Running and looking around

```powershell
.\run.ps1                      # migrations + server with auto-reload, http://127.0.0.1:8000
```

- **Swagger UI** at http://127.0.0.1:8000/docs: try every route; it shows each request and response model.
- **Logs:** our own loggers (`app.*`) print at INFO. To see message text and tool arguments too, set the level to
  `logging.DEBUG` in `setup_logging()` (`core/logging.py`) while debugging; don't commit that.
- **A scratch database:** point `DATABASE_URL` at a copy to experiment without touching your data:
  `$env:DATABASE_URL = "sqlite:///C:/temp/try.db"` (then run the migrations against it).

## Python features you'll see

| Feature | Where | Why |
|---|---|---|
| Pydantic `BaseModel`, `Field`, `Annotated[...]` | messages, `values.py`, `models.py`, schemas | validation at the edges; `Annotated` types like `RecordId`, `Amount`, `Merchant` carry their rules everywhere they're used |
| `model_config = ConfigDict(frozen=True, extra="forbid")` | every message | a message can't be changed, and a misspelt field is an error |
| `StrEnum` | `PaymentMethod`, `ToolName`, `ActionName`, ... | named values that still compare equal to their strings |
| `Protocol` | `Clock`, `ToolCallingModel`, `StructuredOutputModel`, `ExpenseTools`, `Surface` | ports: what's needed, not which class provides it |
| generators (`yield`, `yield from`) | the agent loop, the AG-UI stream | events as they happen; `result = yield from f()` passes events up and returns a value |
| `ContextVar` | `core/cqrs.py` | the unit of work in progress, per request thread |
| `match` statements | the Gemini adapter, conversations | translating message kinds |

## Anatomy of a module

```
modules/expenses/
  __init__.py              the contract other modules may import: re-exports messages, read models, enums, limits
  commands/                one file per command: the message and its handler, (ctx, command) -> id | None
    create_expense.py      CreateExpense + create_expense
    update_expense.py      UpdateExpense, ExpenseChanges + update_expense
    delete_expense.py      DeleteExpense + delete_expense
  queries/                 one file per query: the message, a result only it returns, its handler, (ctx, query) -> DTO
    get_expense.py         GetExpense + get_expense
    list_expenses.py       ListExpenses + list_expenses
    get_monthly_summary.py GetMonthlySummary, MonthlySummary, CategoryTotal + get_monthly_summary
    get_monthly_trend.py   GetMonthlyTrend, MonthlyTrend, MonthTotal + get_monthly_trend
    month_range.py         the date-and-currency filter the summary and the trend share
  values.py                ExpenseId, Annotated field types (Amount, Merchant, Note, Version), PaymentMethod and
                           its labels, limits
  models.py                read models several slices return: ExpenseRead, ExpenseList, Totalled
  domain/rules.py          rules that hold however a change arrives: require_positive_amount,
                           require_category_exists
  persistence/
    tables.py              SQLModel tables (private) + TABLES
    repository.py          the write side's table access: get, add, remove (stages only; never commits)
  api.py                   FastAPI router: HTTP -> messages
  module.py                for bootstrap.py: register_handlers(bus), router, TABLES
```

`categories` and `conversations` have the same shape, without what they don't need: neither has `domain/` or a
repository, and `conversations` has no `models.py` (its one read model, `ThreadRead`, lives in
`queries/get_thread.py`; `queries/thread_rows.py` is the row reading `GetHistory` and `GetThread` share).

**Why vertical slices.** A message and its handler change together, so they live in one file: to change a use case
you open one file, and to add one you write one file and add one `bus.register` line. Each handler is named like
its file (`get_monthly_summary.py` holds `get_monthly_summary`). Only what several slices share sits beside them,
in a file or folder named for its role (`values.py`, `models.py`, `domain/`, `persistence/`). A slice may import
another slice's message to send it through the bus (`create_category` asks `FindCategoryByName`), never its handler.

**The contract is still the package.** Other modules write `from app.modules import expenses` and use
`expenses.CreateExpense`; they never import a slice file. Because `__init__.py` re-exports from the slices,
importing the package also loads the module's handlers and tables (not its routes, and not the database engine):
the price of keeping each message beside its handler. Module dependencies run one way (expenses → categories;
mcp → expenses, categories; assistant → the rest), so this can't create an import cycle. See D175.

A handler gets a `Context`: `ctx.session` (the unit of work's session), `ctx.bus` (to ask other modules, in the same
transaction) and `ctx.clock`.

## Recipe: add a query

Say the Dashboard needs "how much was spent at one merchant". In the **expenses** module:

**1. The slice** (a new file, `queries/get_merchant_total.py`): the question, its answer and the handler, together.
The handler is named like the file, reads straight into the answer, and changes nothing.

```python
"""GetMerchantTotal: everything spent at one merchant. The query, its answer and its handler."""

from sqlalchemy import func
from sqlmodel import col, select

from app.core.cqrs import Context, Query
from app.core.money import DEFAULT_CURRENCY, CurrencyCode
from app.modules.expenses.models import Totalled
from app.modules.expenses.persistence.tables import Expense
from app.modules.expenses.values import Merchant


# GetMerchantTotal's answer: total_minor + a computed rupee `total` (from Totalled), per merchant.
class MerchantTotal(Totalled):
    merchant: str
    expense_count: int


class GetMerchantTotal(Query[MerchantTotal]):
    """Everything spent at one merchant (any letter case), in one currency."""

    merchant: Merchant                 # reuse the shared Annotated types (values.py): same rules everywhere
    currency: CurrencyCode = DEFAULT_CURRENCY


def get_merchant_total(ctx: Context, query: GetMerchantTotal) -> MerchantTotal:
    """Count and add up the merchant's expenses in the database; only the totals travel to Python."""
    statement = select(func.count(col(Expense.id)), func.coalesce(func.sum(Expense.amount_minor), 0)).where(
        func.lower(Expense.merchant) == func.lower(query.merchant), Expense.currency == query.currency
    )
    count, total = ctx.session.exec(statement).one()
    return MerchantTotal(merchant=query.merchant, expense_count=count, total_minor=total)
```

If another slice needs the same filter or answer later, move it to the shared place for its role (`models.py`,
`values.py`, or a helper beside the slices like `queries/month_range.py`) rather than importing one slice from another.

**2. Register it** (`module.py`): import the message and handler from the slice, and add one line,
`bus.register(GetMerchantTotal, get_merchant_total)`. Registering twice is an error at start-up, and asking an
unregistered message is a `LookupError`: wiring mistakes fail loudly.

**3. Export it** (`__init__.py`) if other modules may ask it: import `GetMerchantTotal` and `MerchantTotal` from the
slice and add both to `__all__`.

**4. A route** (`api.py`), if the web app needs it, importing from the slice:

```python
@router.get("/merchants/{merchant}/total")
def merchant_total(merchant: str, bus: BusDep) -> MerchantTotal:
    return bus.ask(GetMerchantTotal(merchant=merchant))
```

**5. Regenerate the web contract**, so the web app gets the new types:

```powershell
.\.venv\Scripts\python.exe backend\scripts\export_contracts.py
cd web; npm run gen:api
```

## Recipe: add a command

Commands follow the same steps (a new file in `commands/`, one `bus.register` line, an export if others send it),
with three differences:

- the handler **changes data** and returns **at most an id** (`Command[int]` or `Command[None]`); a route that must
  answer with data sends the command, then asks a query;
- business rules raise `BusinessRuleError`; a rule several commands share goes in `domain/rules.py`, one only this
  command applies can stay in its handler;
- writes go through the repository (`persistence/repository.py`), which only stages them. **Never call
  `session.commit()`**: the bus commits once, after the handler returns, and rolls back if anything raised. A command
  sent from inside another runs in a SAVEPOINT.

```python
# commands/archive_expense.py (after its module docstring and imports)
class ArchiveExpense(Command[None]):
    expense_id: ExpenseId


def archive_expense(ctx: Context, command: ArchiveExpense) -> None:
    expense = repository.get(ctx.session, command.expense_id)   # NotFoundError if missing
    if expense.archived:
        raise BusinessRuleError(f"Expense {expense.id} is already archived")
    expense.archived = True
    expense.version += 1                                        # every change raises the version
```

Then `bus.register(ArchiveExpense, archive_expense)` in `module.py`.

To run several commands as one transaction (all saved, or none), wrap them: `with bus.unit_of_work(): ...`.

## Recipe: use another module

Import its **package**, send its **messages**. This is the expenses module's rule that a category must exist
(`expenses/domain/rules.py`):

```python
from app.modules import categories     # never app.modules.categories.queries.get_category or .persistence.tables

def require_category_exists(ctx: Context, category_id: int) -> None:
    if ctx.bus.ask(categories.GetCategory(category_id=category_id)) is None:
        raise BusinessRuleError(f"Category {category_id} does not exist")
```

Store another module's things as **plain ids** (no foreign keys across modules), and handle the case where one has
disappeared.

## Recipe: add or change a table

1. Change the module's `persistence/tables.py` (and add a new table to its `TABLES`). A column's length comes from a
   limit in `values.py`, so the messages and the table agree.
2. Generate a migration, then **read it** (autogenerate is a draft):
   ```powershell
   .\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini revision --autogenerate -m "expenses get archived"
   ```
3. Check the file in `backend/migrations/versions/`: column types, a `server_default` for new NOT NULL columns on
   existing rows, batch mode for SQLite (`op.batch_alter_table`), and a `downgrade()` that really undoes it.
4. Data conversions go in the migration itself, written out, not imported from app code (see 0002).
5. Apply it: `.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head` (or restart `run.ps1`).
6. Try `downgrade -1` and `upgrade head` again on a **copy** of your database.

The whole upgrade runs in one transaction: if it fails, nothing changed. Details: [database_schema.md](database_schema.md).

## Recipe: add a module

For example, budgets:

1. The module's folder, as vertical slices like the others:

   ```
   modules/budgets/
     __init__.py                re-exports the contract: messages, read models, ids, limits
     values.py                  BudgetId, field types, limits (imports no other file of the module)
     commands/create_budget.py  CreateBudget + create_budget
     queries/get_budget.py      GetBudget, its answer + get_budget
     persistence/tables.py      the Budget table + TABLES
     api.py                     the routes
     module.py                  register_handlers(bus): one bus.register per message; router; TABLES
   ```

   Each folder has an `__init__.py` whose docstring says what it holds. Add `models.py` (read models),
   `domain/rules.py` (shared rules) or `persistence/repository.py` (the write side's table access) once several
   slices need them.
2. Add `budgets_module` to `MODULES` and its router to `api_routers()` in `app/bootstrap.py`.
3. A migration for its tables.
4. Regenerate the web contract.
5. Document it: [architecture.md](architecture.md)'s interface table, [api_endpoints.md](api_endpoints.md),
   [database_schema.md](database_schema.md), and a decision in [decisions.md](decisions.md).

## Recipe: give the assistant a new tool

1. In `modules/mcp/contracts.py`: the tool's name in `ToolName`, and a result model.
2. A new file, `modules/mcp/tools/<tool>.py`, with a `register_<tool>(server, bus, views)` function holding the
   tool: a description, typed `Annotated` arguments (with descriptions: the model reads them), the right annotations
   (`READS_ONLY`, `ADDS_DATA`, `CHANGES_DATA`), and its body inside `with tool_errors():`, sending commands and
   queries through the bus. Those pieces come from `tools/support.py`. Optional text arguments are `str = ""`.
   Constants only the tool uses stay in its file (`MAX_ROWS` in `tools/list_expenses.py`).
3. Add the registrar to `TOOL_REGISTRARS` in `mcp/server.py` (the order there is the order the model sees the
   tools in).
4. Optional: a card in `assistant/a2ui/cards.py` (`_CARDS`) and chip labels in `assistant/api/agui_stream.py`
   (`TOOL_LABELS`).
5. Restart: the assistant lists tools once.

## Errors: which to raise

| Raise | When | Becomes |
|---|---|---|
| `NotFoundError` | the thing asked for doesn't exist | 404 problem; an MCP tool error |
| `BusinessRuleError` | the request is fine but breaks a rule | 422 problem; an MCP tool error |
| `ExternalServiceError` (e.g. `LlmError`) | a service we depend on failed | 502 problem; an AG-UI `RUN_ERROR` |
| anything else | a bug | 500 problem with a generic message; details in the log |

Never catch exceptions in a route: `core/errors.py` turns them into problem responses in one place.

## Helpers to use, not reinvent

| Need | Use |
|---|---|
| today / now | `ctx.clock.today()`, `ctx.clock.now()` in handlers; `ClockDep` in routes. Never `date.today()` |
| a month like `2026-11` | `YearMonth.parse()`, `.first_day()`, `.shift(n)`, `str()` (`core/months.py`) |
| money | `rupees_to_paise`, `paise_to_rupees`, `format_money` (`core/money.py`); never `float` |
| an id from a client | `RecordId` (bodies, `core/ids.py`), `IdPath` (URL paths, `core/dependencies.py`) |
| currency codes | `CurrencyCode` / `CURRENCY_PATTERN` |
| an expense's fields | `ExpenseId`, `Amount`, `Merchant`, `Note`, `Version`, `PaymentMethod` and the limits (`expenses/values.py`) |
| a total in paise and rupees | subclass `Totalled` (`expenses/models.py`): `total_minor` plus a computed `total` |
| "this month, in this currency" | `in_month_range(start, end, currency)` (`expenses/queries/month_range.py`) |
| an expense rule | `require_positive_amount`, `require_category_exists` (`expenses/domain/rules.py`) |
| an MCP tool's pieces | `tool_errors()`, `given()`, `READS_ONLY` / `ADDS_DATA` / `CHANGES_DATA`, `ExpenseIdArg` (`mcp/tools/support.py`) |
| the LLM | the injected model port (`core/llm`: depend on `StructuredOutputModel` or `ToolCallingModel`, whichever you call); never import the Gemini adapter outside `bootstrap.py` |

## Plugging in fakes

Every outside dependency can be replaced through the composition root, without patching modules:

```python
from app import bootstrap, migrations
from app.core.db import create_db_engine
from app.main import create_app
from fastapi.testclient import TestClient

engine = create_db_engine("sqlite://")         # in memory (or "sqlite:///copy.db" for a file)
migrations.upgrade_to_latest(engine)           # the real schema, built by the real migrations
services = bootstrap.build(clock=FixedClock(), llm=ScriptedModel(), engine=engine)
client = TestClient(create_app(services))      # the real routes, bus and MCP server, with your fakes
```

`build()` also takes `tools=` (any `ExpenseTools`); pass it if your `.env` sets `MCP_URL`, or the default tools talk to
that server (and its database). Use cases take their ports directly (`Assistant(bus, tools, llm)`,
`ExpenseParser(bus, llm)`, `Agent(llm, tools)`), and `GeminiModel(api_key, model, client_factory=...)` takes a fake SDK
client. A fake model only needs the method its user calls: `ask_for_json` for `/parse`, `stream_with_tools` for the
agent.

## Conventions

- **Inline documentation** (D171):
  - every file starts with a module docstring: what it's for, its layer (contract, handler, adapter, port...), who
    uses it;
  - every function, method and class has a docstring: what it's for, what it returns and raises, the rule it enforces;
  - business rules are explained where they're applied, saying **why** (money in paise, versions, approvals...);
  - **except docstrings that are data:** Pydantic models (commands, queries, results, tables), enums, FastAPI route
    functions and MCP tools get `#` comments above them instead. Pydantic, FastAPI and the MCP SDK copy those
    docstrings into JSON schemas: the OpenAPI document, the MCP tools' schemas, and the schema Gemini answers
    `/parse` in. Editing one changes what clients and the model see.
- **Comments say why**, in plain words, next to the code they explain.
- **No magic strings or numbers:** a name, key, limit or label is an enum or constant, defined once, in the module that
  owns it, and exported if others need it. Values the web app needs go through `export_contracts.py`.
- **No duplication:** shared rules live in `Annotated` types (`values.py`), `domain/rules.py` or `core/`.
- **Vertical slices:** one file per command or query, holding the message and its handler (named like the file);
  what several slices share goes in `values.py`, `models.py`, `domain/` or `persistence/`, never in one slice that
  others import.
- **Boundaries:** `core/` imports no module; a module imports another's package only; only `bootstrap.py` and
  `main.py` import a `module.py`; inside the assistant, imports run `api/` → `application/` → the rest.
- **Logging:** `logger = logging.getLogger(__name__)`; user data only at DEBUG.
- **Pins:** a new dependency gets an exact version in `requirements.txt`.

## Checking your change

Automated tests aren't part of the repository yet. Until they are, before asking for a review:

1. `.\.venv\Scripts\python.exe -m compileall -q backend\app` compiles.
2. The server starts (`run.ps1`), and the change works in Swagger UI, on a scratch database if it changes data.
3. Migrations go up, down and up again on a copy.
4. The web contract is regenerated and `npm run build` passes in `web/`.
5. The docs are updated in the same commit ([README.md](README.md#keeping-these-docs-current)).

### Review checklist

- [ ] Commands return at most an id; queries change nothing; no `commit()` outside the bus
- [ ] A new command or query is one slice file (message + handler, named like the file), registered in `module.py`,
      exported from `__init__.py` if other modules use it
- [ ] Files under ~180 code lines, functions under ~50; extend through tables and protocols, not new branches
- [ ] No import of another module's files, or of another slice's handler; `core/` untouched by module imports
- [ ] Inputs validated by contract types; business rules raise `BusinessRuleError`
- [ ] No literal names, keys or limits that already exist elsewhere
- [ ] Time from the clock, money in paise
- [ ] New files, functions and rules documented (a docstring, or a `#` comment on schema classes, routes and tools)
- [ ] A migration for every table change, with a working downgrade
- [ ] User data not logged at INFO
- [ ] Docs and the web contract updated
