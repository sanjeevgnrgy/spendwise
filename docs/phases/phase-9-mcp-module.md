# Phase 9: MCP module

> **Later changes:**
> **Refactor (after Phase 18):** the server is built by `create_server(bus)`; tools return typed results
> (`outputSchema`); new `get_expense`; `delete_expense` needs a strict `confirmed=true`; `/mcp/` is served over HTTP
> only with `MCP_TOKEN`, as a bearer token. See [refactor-architecture.md](refactor-architecture.md).

**Goal:** expose SpendWise's expense tools and data over the **Model Context Protocol (MCP)**, so any MCP-capable
AI app (MCP Inspector, Claude Desktop, and later our own assistant) can use them. The server is mounted in the
FastAPI app at `/mcp/`, and can also run over stdio for local tools.

> **Later changes:** in Phase 10 the assistant's agent became an MCP client of this server and
> `assistant/tools.py` was deleted, so "three adapters" below became two adapters plus one MCP client.
> In Phase 15 the tools gained MCP annotations (`read_only_hint`, `destructive_hint`), which the assistant uses to know
> when data changed ([decisions.md](../decisions.md) D111). In Phase 18 `get_summary` also returns `previous_month`
> (its total, for comparisons), alongside the fields it already had.

## Design

**MCP** is a standard way for AI apps to plug into tools and data. In Phase 7 we described our tools to Gemini in
Gemini's own format, inside our own app. MCP describes them once, in a shared format, so *any* compliant AI app
can discover and call them. Think of USB: one plug shape, and any device works with any computer.

**Host, client and server:**
- **Host:** the AI app the person uses, such as Claude Desktop, an IDE, or the MCP Inspector. It contains the model
  and decides what the model may do.
- **Client:** a connector *inside* the host. The host creates one client per server; each client keeps one
  connection and speaks the protocol.
- **Server:** a program that offers capabilities. Ours is `spendwise`, and it offers tools and resources.

Analogy: a laptop (host) has USB ports (clients), and each port connects to one device (server).

**Tools vs resources:**
- **Tools are actions the model chooses to call,** with arguments, and they can change things: `add_expense`,
  `delete_expense`. Like `POST`/`PATCH`/`DELETE` (and searches with parameters).
- **Resources are read-only data, addressed by a URI,** which the host application loads as context:
  `expenses://categories`, `expenses://recent`. Like a `GET` of a known document. The *app or user* usually decides
  to attach a resource; the *model* decides to call a tool.

**Why the MCP module is "just another adapter".** SpendWise now has three ways in:

```
REST router   (HTTP + JSON, for the web frontend)  ─┐
Assistant     (Gemini function calling, /chat)     ─┼─>  expenses / categories services  ─>  database
MCP module    (MCP, for any AI app)                ─┘        (the business rules live here)
```

Each adapter only translates its own protocol into calls to the same public service functions. The MCP module
owns no tables and contains no business rules. So "amount must be greater than 0" and "the category must exist"
apply to an MCP call exactly as they do to `POST /expenses`, without being written again.

**Two transports, one server:**
- **stdio:** the host starts our script as a child process and talks through its stdin/stdout. Local only, no
  network, no port. Used by Claude Desktop and `mcp dev`.
- **Streamable HTTP:** the server is reachable at a URL (`http://127.0.0.1:8000/mcp/`), for clients that connect
  over the network. Mounted inside the FastAPI app.

## What was built

| File | What |
|---|---|
| `modules/mcp/server.py` | **New.** `server = MCPServer("spendwise")`, 5 tools, 2 resources |
| `modules/mcp/__init__.py` | **New.** Says what the module is; exports nothing to other modules |
| `backend/mcp_stdio.py` | **New.** Runs the same server over stdio |
| `app/main.py` | Mounts the server's Streamable HTTP app at `/mcp` and starts its session manager in `lifespan` |
| `requirements.txt` | `mcp[cli]==2.3.0` |

**SDK naming:** in MCP SDK 2.x, the class that tutorials call `FastMCP` is named **`MCPServer`**
(`from mcp.server.mcpserver import MCPServer`). Same idea, new name.

**A tool** is a decorated function. Its docstring and parameter descriptions are what a client's model reads:

```python
@server.tool()
def add_expense(
    amount: Annotated[str, Field(description="Amount as a plain number string, e.g. '450.50'.")],
    category: Annotated[str, Field(description="Category name; see the expenses://categories resource.")],
    ...
) -> dict[str, Any]:
    """Record a new expense. Needs the amount, category, merchant, date and payment method; ..."""
    with _tool_session() as session:
        created = expenses.create_expense(session, expenses.ExpenseCreate(...))   # the public service
        return {"saved": _describe(created, _category_names(session))}
```

**A resource** is a function behind a URI:

```python
@server.resource("expenses://categories", mime_type="application/json")
def categories_resource() -> str:
    """The expense categories that exist (id, name, icon)."""
    with Session(engine) as session:
        return json.dumps([c.model_dump() for c in categories.list_categories(session)])
```

**Mounting it** (`main.py`):

```python
mcp_http_app = mcp_server.streamable_http_app(streamable_http_path="/", stateless_http=True, json_response=True)

@asynccontextmanager
async def lifespan(app):
    create_db_and_tables()
    async with mcp_server.session_manager.run():   # a mounted app's own startup doesn't run
        yield

app.mount("/mcp", mcp_http_app)
```

Details worth knowing:
- **Errors:** the SDK hides the text of unexpected exceptions from clients, because it could leak internals. Only a
  `ToolError`'s message is passed on. `_tool_session()` turns our expected errors (unknown category, amount ≤ 0, bad
  date, missing expense) into `ToolError`s, so the client's model sees *"Unknown category 'Snacks'. Use one of: ..."*
  and can correct itself.
- **Delete still needs confirmation:** `delete_expense(confirmed=false)` only shows what would be deleted.
- **Sessions:** MCP calls don't pass through FastAPI's `SessionDep`, so each tool opens its own database session.
- **Never `print()` in the stdio script:** stdout carries the protocol. Logging goes to stderr, which is fine.
- **The assistant doesn't use MCP yet.** `assistant/tools.py` and the MCP tools are near-copies for now. A later
  phase makes the assistant call the MCP tools, and the copy goes away ([decisions.md](../decisions.md) D67).

## Run it

From the project folder: `.\run.ps1` (it installs `mcp` first, because `requirements.txt` changed).
The MCP endpoint is then at **`http://127.0.0.1:8000/mcp/`**. Keep the trailing slash; `/mcp` redirects to it.
It doesn't appear in `/docs`, because it isn't a REST route.

## Test it with the MCP Inspector (`mcp dev`)

The Inspector is a web page that acts as a host: it lists a server's tools and resources and lets you call them
by hand. It needs Node.js (for `npx`) and `uv`; both are installed on this machine.

**Over stdio** (the server doesn't need to be running; the Inspector starts it):

```powershell
.\.venv\Scripts\mcp.exe dev backend\mcp_stdio.py
```

The first run downloads the Inspector and asks to proceed. It then prints a local URL and opens it in your browser.

1. Click **Connect**. (Transport "STDIO" and the command are already filled in.)
2. **Tools** tab → **List Tools** → you should see `add_expense`, `list_expenses`, `get_summary`, `update_expense`,
   `delete_expense`.
3. Pick **get_summary**, enter `month` = `2026-11`, **Run Tool** → the month's totals as JSON.
4. Pick **add_expense** and enter `amount` `99.50`, `category` `Food`, `merchant` `MCP Cafe`, `spent_on`
   `2026-11-13`, `payment_method` `upi` → `{"saved": {...}}`. Try `amount` `-5` → an error reading
   *"Amount must be greater than 0"*.
5. **Resources** tab → **List Resources** → open `expenses://categories` and `expenses://recent`.

Stop it with Ctrl+C in the terminal.

**Over HTTP** (tests the mounted endpoint): start the app with `.\run.ps1`, then in a second terminal run
`npx @modelcontextprotocol/inspector`. In the page, choose transport **Streamable HTTP**, URL
`http://127.0.0.1:8000/mcp/`, and **Connect**.

Both use your real `backend/spendwise.db`, so expenses you add there are real; delete them afterwards if you like.

**What was checked while building it:** a script using the SDK's own MCP client ran the same sequence over
**both** stdio and the mounted HTTP endpoint, against a throwaway database. It listed the 5 tools and 2 resources,
read both resources, added, listed, updated and summarised an expense, saw clear errors for a negative amount and an
unknown category, and saw delete refuse without `confirmed` and succeed with it. REST routes kept working alongside.
The Inspector UI itself wasn't opened (it launches a browser); `uv run` was checked to use the project's `.venv`.

## Bonus: add it to Claude Desktop

Claude Desktop is an MCP host. It starts stdio servers listed in its config file.

**Option 1, by hand.** In Claude Desktop: **Settings → Developer → Edit Config**, which opens
`%APPDATA%\Claude\claude_desktop_config.json`. Add (with your real paths, and doubled backslashes):

```json
{
  "mcpServers": {
    "spendwise": {
      "command": "C:\\path\\to\\project\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\project\\backend\\mcp_stdio.py"]
    }
  }
}
```

**Option 2:** `.\.venv\Scripts\mcp.exe install backend\mcp_stdio.py --name spendwise` writes a similar entry for you.
Check the entry afterwards: it should start the server with this project's Python, as in option 1.

Then quit Claude Desktop completely (from the system tray) and reopen it. The SpendWise tools appear in the chat's
tools menu; ask *"What did I spend on food this month?"*. This wasn't tried while building the phase.

No API key goes in that config: the MCP server doesn't call Gemini. It reads `.env` and the database by absolute
path, so it works no matter which folder Claude Desktop starts it from.

## Design questions

**1. You connect the MCP Inspector to SpendWise. Which is the host, which is the client, and which is the server?**

<details><summary>Answer</summary>

The Inspector web app is the **host** (it's the application a person uses). Inside it, the connection object it
creates for SpendWise is the **client**. Our `spendwise` MCPServer, running as `mcp_stdio.py` or at `/mcp/`, is
the **server**. With Claude Desktop it's the same picture: Claude Desktop is the host, it creates one client per
configured server, and SpendWise is one of those servers.
</details>

**2. Why is `expenses://categories` a resource, while `list_expenses` is a tool?**

<details><summary>Answer</summary>

The category list is a small, fixed piece of read-only data with no arguments: something a host can load as
context under a known address. That's a resource. `list_expenses` takes arguments (dates, category, search text)
that the *model* chooses based on the question, so it's a tool. Anything that changes data (`add`, `update`,
`delete`) must also be a tool.
</details>

**3. Someone calls `add_expense` over MCP with amount `-5`. Where is that rejected, and why didn't we have to write
that rule in the MCP module?**

<details><summary>Answer</summary>

In `expenses.create_expense()`, the expenses module's service, which raises `BusinessRuleError("Amount must be
greater than 0")`. The MCP tool only translates the MCP call into that service call (and the error into a
`ToolError` the client can read). Because the REST router, the assistant and the MCP module are all adapters over
the same services, every rule is written once and applies to all three.
</details>
