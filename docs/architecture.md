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
        db.py           engine, table creation, get_session / SessionDep
        errors.py       NotFoundError (404), BusinessRuleError (422), ExternalServiceError (502), handlers
        logging.py      console logging for spendwise.* loggers
        money.py        rupees <-> paise
        llm.py          ask_gemini(), ask_gemini_for_json(), stream_gemini_with_tools()
      modules/
        assistant/      POST /ask, /parse, /chat, /agent (AG-UI stream), GET /threads; ChatMessage table (parse, agent, mcp_client)
        mcp/            MCP server "spendwise": 5 tools, 2 resources; mounted at /mcp/ (no tables)
        categories/     Category table, GET /categories, public interface
        expenses/       Expense table, CRUD routes + GET /summary, /summary/trend, public interface
    seed.py             sample data, using modules' public interfaces
    mcp_stdio.py        runs the MCP server over stdio (Inspector, Claude Desktop)
  agents/               (planned) A2A agents: receipt, insights, currency; separate services
  skills/               (planned) Agent Skills
  web/                  React + Vite + TypeScript, Tailwind, shadcn/ui (talks to the backend over HTTP)
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
7. **`core/` never imports from `modules/`.** It holds config, db, errors, money and the LLM client;
   logging and events come later.
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
| `categories` | `CategoryCreate`, `CategoryRead`, `create_category`, `get_category`, `list_categories` | `expenses`, `assistant`, `seed.py` |
| `expenses` | `ExpenseCreate`, `ExpenseUpdate`, `ExpenseRead`, `ExpenseFilters`, `MonthlySummary`, `CategoryTotal`, `PaymentMethod`, `create_expense`, `get_expense`, `list_expenses`, `update_expense`, `delete_expense`, `monthly_summary`, `monthly_trend` (+ `MonthlyTrend`, `MonthTotal`) | `mcp`, `assistant` (`PaymentMethod` only, for `/parse`), `seed.py` |
| `assistant` | nothing yet | — |

| `mcp` | nothing | — (it *uses* `expenses` and `categories`) |

Routers and the MCP `server` object are not part of any public interface; only `main.py` (and `mcp_stdio.py`)
import them.

**Two adapters, one set of services.** The REST routers and the MCP module each translate their own protocol
(HTTP/JSON, MCP) into calls to the same public service functions. The business rules live in the services, so they
apply to every way in.

**The assistant's agent goes through MCP** (since Phase 10). It doesn't import the expenses module: it connects to
`MCP_URL` as an MCP client, discovers the tools there, and asks the MCP server to run them. By default that URL is
this same app, so `/chat` makes HTTP calls to `/mcp/` on its own server.

## How a request flows

`POST /ask`:

```
HTTP request
  -> main.py (app)                      includes the assistant router
  -> modules/assistant/router.py        validates the body (AskRequest)
  -> modules/assistant/service.py       answer(prompt): orchestration grows here later
  -> core/llm.py                        ask_gemini(): the only code that talks to Gemini
  -> Gemini API
```

`POST /expenses`:

```
HTTP request
  -> modules/expenses/router.py         FastAPI validates the body (ExpenseCreate) -> 422 with a list if malformed
  -> modules/expenses/service.py        create_expense(): amount > 0? category exists?
       -> categories.get_category()     public interface of another module: "does category 3 exist?"
       -> rupees_to_paise()             core/money.py
       -> expenses/repository.add()     the only code that writes the expense table
  <- ExpenseRead (frozen copy)           router returns it with 201
```

`POST /parse`:

```
HTTP request
  -> modules/assistant/router.py        validates the body (ParseRequest)
  -> modules/assistant/service.py       parse_expense_text(): today's date + category names
       -> categories.list_categories()  public interface: the names Gemini may choose from
  -> modules/assistant/parse.py         builds the schema (category enum) and system instruction
  -> core/llm.ask_gemini_for_json()     structured output: JSON shaped by the schema
  <- ParsedExpense + missing_fields      validated with Pydantic; nothing is saved
```

`POST /chat`:

```
HTTP request
  -> modules/assistant/router.py        validates the body (ChatRequest: message, optional thread_id)
  -> modules/assistant/service.py       chat(): new thread, or load its last 10 turns
       -> assistant/repository.py       ChatMessage rows (the assistant module's own table)
  -> modules/assistant/agent.py         run(): waits for agent.stream(), the loop (at most 5 Gemini calls):
       -> assistant/mcp_client.py              lists the tools and categories from the MCP server (MCP_URL)
       -> core/llm.stream_gemini_with_tools()  Gemini streams text and/or function calls; steps rebuilt from the pieces
       -> assistant/mcp_client.call_tool()     HTTP to /mcp/ -> modules/mcp/server.py -> expenses/categories services
  -> assistant/repository.add_turn()    saves every step of this turn, in one commit
  <- ChatResponse(thread_id, reply, tool_calls)   every step, tool call and token count is logged
```

`POST /agent` (AG-UI over Server-Sent Events; the chat panel uses this one):

```
HTTP request
  -> modules/assistant/router.py        validates the body (ag_ui RunAgentInput) -> 422 if malformed; then a 200 stream
       (a sync generator with EventSourceResponse: FastAPI runs it in a worker thread and pings every 15 s)
  -> modules/assistant/service.py       agent_run(): RUN_STARTED; newest user message; load the thread (new if unknown)
  -> modules/assistant/agent.py         stream(): the same loop as /chat, yielding text pieces as Gemini writes them
       each piece                         -> TEXT_MESSAGE_START (first piece only), TEXT_MESSAGE_CONTENT
  -> assistant/repository.add_turn()    saves the turn when the loop ends
  <- TEXT_MESSAGE_END, RUN_FINISHED(result={"toolCalls": [...]})   or RUN_ERROR on any failure (nothing saved)
```

If a service raises `NotFoundError`, `BusinessRuleError` or `ExternalServiceError` (e.g. `GeminiError`), the
handlers registered from `core/errors.py` turn it into a 404, 422 or 502 response. Routers never catch anything
themselves.

## Startup

`main.py` imports each module's router. That also imports the module itself, which defines its table classes
and registers them with SQLModel. The app's `lifespan` then calls `create_db_and_tables()`, which creates
every registered table that doesn't exist yet. `core` can't do the importing itself, because core never
imports modules.

## Adding a new module

1. Create `backend/app/modules/<name>/` with an `__init__.py` docstring saying what the module is for.
2. Add only the layers you need: `models.py` (tables), `schemas.py` (DTOs), `repository.py` (database
   access), `service.py` (rules, returns DTOs), `router.py` (HTTP).
3. Export the public interface from `__init__.py` with `__all__`.
4. Need another module? Import it as `from app.modules import <other>` and use only its exports.
5. In `main.py`: import the module if it has tables, and `include_router` if it has routes.
6. Document it: phase notes, plus [decisions.md](decisions.md) for any new decision.

## Checking the rules

Nothing checks the rules automatically at the moment: the architecture test was removed along with the other
tests (see [decisions.md](decisions.md) D64). These scans, run from the project folder, catch violations:

```powershell
# Core must never import modules. Expect no output.
Select-String -Path backend\app\core\*.py -Pattern '^\s*(from|import)\s+app\.modules'

# Imports that reach into a module's internals. Each line must be inside that same module's folder
# (e.g. categories/service.py importing app.modules.categories.repository is fine).
Select-String -Path backend\app\modules\*\*.py -Pattern '^\s*(from|import)\s+app\.modules\.'
```

`main.py` (the composition root) is allowed to import routers.
