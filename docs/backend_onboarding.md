# Backend Onboarding

A working guide to the backend (`backend/`): how it's put together, the patterns you'll meet, and step-by-step
recipes for the changes you'll make most. Read [architecture.md](architecture.md) first for the rules; this page is
the "how".

## The mental model in five lines

1. A **module** per business domain (`categories`, `expenses`, `conversations`, `assistant`) owns its tables.
2. Every operation is a **command** (changes data, returns at most an id) or a **query** (reads), a small frozen
   Pydantic model with **one handler**.
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
| Pydantic `BaseModel`, `Field`, `Annotated[...]` | contracts, schemas | validation at the edges; `Annotated` types like `RecordId`, `Amount`, `Merchant` carry their rules everywhere they're used |
| `model_config = ConfigDict(frozen=True, extra="forbid")` | every message | a message can't be changed, and a misspelt field is an error |
| `StrEnum` | `PaymentMethod`, `ToolName`, `ActionName`, ... | named values that still compare equal to their strings |
| `Protocol` | `Clock`, `ToolCallingModel`, `StructuredOutputModel`, `ExpenseTools`, `Surface` | ports: what's needed, not which class provides it |
| generators (`yield`, `yield from`) | the agent loop, the AG-UI stream | events as they happen; `result = yield from f()` passes events up and returns a value |
| `ContextVar` | `core/cqrs.py` | the unit of work in progress, per request thread |
| `match` statements | the Gemini adapter, conversations | translating message kinds |

## Anatomy of a module

```
modules/expenses/
  __init__.py      the contract other modules may import: commands, queries, DTOs, enums, limits
  contracts.py     those definitions
  domain.py        business rules that hold however a change arrives (amount > 0)
  tables.py        SQLModel tables (private) + TABLES
  repository.py    the write side's table access: get, add, remove (stages only; never commits)
  commands.py      one function per command: (ctx, command) -> id | None
  queries.py       one function per query: (ctx, query) -> DTO; SQL straight into read models
  api.py           FastAPI router: HTTP -> messages
  module.py        for bootstrap.py: register_handlers(bus), router, TABLES
```

A handler gets a `Context`: `ctx.session` (the unit of work's session), `ctx.bus` (to ask other modules, in the same
transaction) and `ctx.clock`.

## Recipe: add a query

Say the Dashboard needs "how much was spent at one merchant". In the **expenses** module:

**1. The contract** (`contracts.py`): the question and its answer.

```python
class MerchantTotal(_Totalled):        # total_minor + a computed rupee `total`
    merchant: str
    expense_count: int


class GetMerchantTotal(Query[MerchantTotal]):
    """Everything spent at one merchant (any letter case), in one currency."""

    merchant: Merchant                 # reuse the shared Annotated types: same rules everywhere
    currency: CurrencyCode = DEFAULT_CURRENCY
```

**2. The handler** (`queries.py`): read straight into the answer; change nothing.

```python
def merchant_total(ctx: Context, query: GetMerchantTotal) -> MerchantTotal:
    statement = select(func.count(col(Expense.id)), func.coalesce(func.sum(Expense.amount_minor), 0)).where(
        func.lower(Expense.merchant) == func.lower(query.merchant), Expense.currency == query.currency
    )
    count, total = ctx.session.exec(statement).one()
    return MerchantTotal(merchant=query.merchant, expense_count=count, total_minor=total)
```

**3. Register it** (`module.py`): `bus.register(GetMerchantTotal, queries.merchant_total)`. Registering twice is an
error at start-up, and asking an unregistered message is a `LookupError`: wiring mistakes fail loudly.

**4. Export it** (`__init__.py`) if other modules may ask it.

**5. A route** (`api.py`), if the web app needs it:

```python
@router.get("/merchants/{merchant}/total")
def merchant_total(merchant: str, bus: BusDep) -> MerchantTotal:
    return bus.ask(GetMerchantTotal(merchant=merchant))
```

**6. Regenerate the web contract**, so the web app gets the new types:

```powershell
.\.venv\Scripts\python.exe backend\scripts\export_contracts.py
cd web; npm run gen:api
```

## Recipe: add a command

Commands follow the same steps, with three differences:

- the handler **changes data** and returns **at most an id** (`Command[int]` or `Command[None]`); a route that must
  answer with data sends the command, then asks a query;
- business rules go in `domain.py` (or the handler) and raise `BusinessRuleError`;
- writes go through the repository, which only stages them. **Never call `session.commit()`**: the bus commits once,
  after the handler returns, and rolls back if anything raised. A command sent from inside another runs in a
  SAVEPOINT.

```python
class ArchiveExpense(Command[None]):
    expense_id: ExpenseId


def archive_expense(ctx: Context, command: ArchiveExpense) -> None:
    expense = repository.get(ctx.session, command.expense_id)   # NotFoundError if missing
    if expense.archived:
        raise BusinessRuleError(f"Expense {expense.id} is already archived")
    expense.archived = True
    expense.version += 1                                        # every change raises the version
```

To run several commands as one transaction (all saved, or none), wrap them: `with bus.unit_of_work(): ...`.

## Recipe: use another module

Import its **package**, send its **messages**:

```python
from app.modules import categories                     # never app.modules.categories.tables / queries

def _require_category(ctx: Context, category_id: int) -> None:
    if ctx.bus.ask(categories.GetCategory(category_id=category_id)) is None:
        raise BusinessRuleError(f"Category {category_id} does not exist")
```

Store another module's things as **plain ids** (no foreign keys across modules), and handle the case where one has
disappeared.

## Recipe: add or change a table

1. Change the module's `tables.py` (and add a new table to its `TABLES`).
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

1. `backend/app/modules/budgets/` with `contracts.py`, `tables.py`, `commands.py`, `queries.py`, `api.py`,
   `module.py`, and `__init__.py` exporting the contract.
2. Add `budgets_module` to `MODULES` and its router to `api_routers()` in `app/bootstrap.py`.
3. A migration for its tables.
4. Regenerate the web contract.
5. Document it: [architecture.md](architecture.md)'s interface table, [api_endpoints.md](api_endpoints.md),
   [database_schema.md](database_schema.md), and a decision in [decisions.md](decisions.md).

## Recipe: give the assistant a new tool

1. In `modules/mcp/contracts.py`: the tool's name in `ToolName`, and a result model.
2. In `modules/mcp/read_tools.py` or `write_tools.py`: a `register_<tool>(server, bus, views)` function holding the
   tool, with a description, typed `Annotated` arguments (with descriptions: the model
   reads them), the right annotations (`READS_ONLY`, `ADDS_DATA`, `CHANGES_DATA`), and its body inside
   `with tool_errors():` (`tool_support.py`), sending commands and queries through the bus. Optional text arguments
   are `str = ""`. Then add the registrar to `TOOL_REGISTRARS` in `mcp/server.py` (the order there is the order the
   model sees the tools in).
3. Optional: a card in `assistant/a2ui/cards.py` (`_CARDS`) and chip labels in `assistant/agui.py` (`TOOL_LABELS`).
4. Restart: the assistant lists tools once.

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
- **No duplication:** shared rules live in `Annotated` types, `domain.py` or `core/`.
- **Boundaries:** `core/` imports no module; a module imports another's package only; only `bootstrap.py` and
  `main.py` import a `module.py`.
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
- [ ] Files under ~180 code lines, functions under ~50; extend through tables and protocols, not new branches
- [ ] No import of another module's files; `core/` untouched by module imports
- [ ] Inputs validated by contract types; business rules raise `BusinessRuleError`
- [ ] No literal names, keys or limits that already exist elsewhere
- [ ] Time from the clock, money in paise
- [ ] New files, functions and rules documented (a docstring, or a `#` comment on schema classes, routes and tools)
- [ ] A migration for every table change, with a working downgrade
- [ ] User data not logged at INFO
- [ ] Docs and the web contract updated
