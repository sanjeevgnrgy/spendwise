# How SpendWise Works

The main flows, from a click to the database and back, as diagrams. For the rules behind them see
[architecture.md](architecture.md); for the assistant's internals, [assistant_architecture.md](assistant_architecture.md).

## 1. Adding an expense on the Expenses page

```mermaid
sequenceDiagram
    actor You
    participant Dialog as Add expense dialog<br/>(features/expenses)
    participant Query as TanStack Query
    participant API as POST /api/v1/expenses<br/>(expenses/api.py)
    participant Bus as MessageBus
    participant Cmd as create_expense<br/>(expenses/commands/create_expense.py)
    participant Cat as categories module
    participant DB as SQLite

    You->>Dialog: amount, merchant, category, date, paid with
    Dialog->>Query: useCreateExpense().mutate(toNewExpense(draft))
    Query->>API: JSON body (typed from the OpenAPI contract)
    API->>API: validate the body (CreateExpense) or 422
    API->>Bus: execute(CreateExpense)
    Bus->>DB: open a session (the unit of work)
    Bus->>Cmd: handle
    Cmd->>Cmd: amount > 0?
    Cmd->>Bus: ask(categories.GetCategory)
    Bus->>Cat: same session
    Cat-->>Cmd: exists
    Cmd->>DB: INSERT (staged, flushed for the id)
    Bus->>DB: COMMIT
    API->>Bus: ask(GetExpense(id))
    API-->>Query: 201 + Location + the expense
    Query->>Query: meta.changes = expenses → invalidate expense lists and Dashboard
    Query-->>You: the table reloads; "Expense added"
```

If anything fails along the way (an unknown category, amount 0), the bus rolls the transaction back, the API answers
with a problem (`422 business-rule`), and the dialog stays open with your values and a toast with the reason.

## 2. Loading the Dashboard

```mermaid
flowchart LR
    PAGE["DashboardPage"] --> Q1["useMonthlySummary(this month)"]
    PAGE --> Q2["useMonthlyTrend(6)"]
    PAGE --> Q3["useExpenses({limit: 5})<br/>from features/expenses"]
    PAGE --> Q4["useCategories()<br/>from features/categories"]
    Q1 --> R1["GET /api/v1/summary"] --> H1["GetMonthlySummary<br/>SQL GROUP BY category"]
    Q2 --> R2["GET /api/v1/summary/trend"] --> H2["GetMonthlyTrend<br/>SQL GROUP BY year, month<br/>empty months filled with 0"]
    Q3 --> R3["GET /api/v1/expenses?limit=5"] --> H3["ListExpenses<br/>WHERE … ORDER BY … LIMIT"]
    Q4 --> R4["GET /api/v1/categories"] --> H4["ListCategories"]
```

- The four requests go out together; the backend does the adding up, so only totals and 5 rows travel.
- While any is missing: a skeleton. If loading fails: an error card with **Try again** (it retries only what failed).
  If a later reload fails while numbers are on screen: they stay, with a small "couldn't refresh" notice.
- Each answer is cached under a key (`["dashboard", "summary", "2026-11"]`); outdated requests are cancelled.

## 3. Asking the assistant

```mermaid
sequenceDiagram
    actor You
    participant Panel as Chat panel
    participant Agent as POST /api/v1/agent
    participant Model as Gemini
    participant Tools as MCP server (in-process)

    You->>Panel: "Where did my money go this month?"
    Panel->>Agent: AG-UI run (thread id, message, dataVersion)
    Agent->>Model: history + message + tools
    Model-->>Agent: call get_summary(month=2026-11)
    Agent-->>Panel: chip "Adding up the month…"
    Agent->>Tools: get_summary
    Tools-->>Agent: MonthSpending (typed)
    Agent-->>Panel: chip "Added up the month" + insight card
    Agent->>Model: + the result
    Model-->>Agent: "Most went on Food…" (streamed)
    Agent-->>Panel: the reply, word by word
```

The reply appears as it's written; each tool shows as a chip that turns into a tick or a cross; cards appear with the
tool result they come from.

## 4. Deleting through the assistant

```mermaid
flowchart TD
    A["You: delete #14"] --> B["The model asks to delete"]
    B --> C["Server: look #14 up instead<br/>record a card: snapshot + version"]
    C --> D["Card: Delete this expense? #14<br/>Approve / Cancel"]
    D -->|Cancel| E["Nothing changes<br/>the card is used up"]
    D -->|Approve| F{"Card still valid?<br/>same thread, under 15 min, not used"}
    F -->|no| G["'That card can't be used any more'"]
    F -->|yes| H{"#14 still what the card showed?"}
    H -->|no| I["'I couldn't confirm…'<br/>nothing deleted"]
    H -->|yes| J["DELETE … WHERE id = 14 AND version = 3"]
    J --> K["'Done: #14 is deleted'<br/>pages reload"]
```

The model can't delete in the web panel at all; only your Approve does, and only the exact version you saw.

## 5. Keeping every page in sync

```mermaid
flowchart LR
    subgraph sources ["Something changed expenses"]
        M1["a mutation on the Expenses page<br/>meta.changes = expenses"]
        M2["the assistant<br/>STATE_SNAPSHOT → onDataChanged()"]
    end
    RULE["app/query-client.ts<br/>refreshAfter(STALE_AFTER)"]
    K1["invalidate ['expenses', …]"]
    K2["invalidate ['dashboard', …]"]
    UI["whatever is on screen reloads by itself<br/>(the rest reloads when you open it)"]
    M1 --> RULE
    M2 --> RULE
    RULE --> K1 --> UI
    RULE --> K2 --> UI
```

Features don't know about each other's pages: the expenses feature only says "I changed expenses", the assistant
only says "data changed", and the app decides, in one place, what that makes out of date.

## 6. A request through the backend's layers

```mermaid
flowchart TD
    HTTP["HTTP request"] --> MW["middleware: CORS → unexpected-error safety net"]
    MW --> ROUTE["module api.py<br/>validates input, translates to a message"]
    ROUTE -->|"execute(command)"| BUS["MessageBus<br/>opens the unit of work"]
    ROUTE -->|"ask(query)"| BUS
    BUS --> HANDLER["command or query handler<br/>(its slice: commands/ or queries/)"]
    HANDLER --> DOMAIN["domain rules<br/>(domain/rules.py)"]
    HANDLER --> OTHER["other modules' contracts<br/>(ctx.bus, same session)"]
    HANDLER --> REPO["persistence/: repository (writes)<br/>SQL on its own tables (reads)"]
    REPO --> DB[("database")]
    BUS -->|"command ok: COMMIT<br/>error: ROLLBACK"| DB
    HANDLER -->|"NotFound / BusinessRule / ExternalService"| ERR["web/problems.py<br/>→ RFC 9457 problem"]
```

The MCP server is a second adapter over the same bus, so an expense added from Claude Desktop goes through exactly the
same rules as one added on the web page.
