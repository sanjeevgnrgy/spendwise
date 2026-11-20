# Phase 24: The receipt agent (A2A)

**Goal:** reading a receipt moves out of the monolith into a **remote agent**: its own service, reached over the
Agent2Agent protocol (A2A), that takes a receipt and answers with what it says. The assistant becomes its **client
agent**. Decisions: D195–D198.

**The owner's choices** (asked before building):

- **Two parts.** Part 1: the agent on its own (`agents/receipt`, port 9001), checked with a fake model. Part 2: the
  assistant's A2A client, the switch-over (the receipts module keeps uploads only), and the A2A task id in a
  progress chip.
- **The agent reuses the backend's LLM port and Gemini adapter** (D196), rather than a copy or a shared package.
- **Localhost and a key** (D197): the agent listens on `127.0.0.1` only and answers only requests carrying
  `RECEIPT_AGENT_KEY`.
- Up to 3 live Gemini calls, with a synthetic receipt.

## The ideas

**Client agent and remote agent.** A2A connects two agents that don't share code or memory. The *client agent* has a
job to hand off (the assistant: "read this receipt for this person"); the *remote agent* does it (the receipt
agent). The client first reads the remote agent's **Agent Card**, a JSON document at a well-known URL that says what
the agent is, where to reach it, which skills it has, what media types they take, and how to authenticate. Then it
sends a **message**; the agent turns it into a **task** and answers with **artifacts**, the task's results. It's like
sending a document to a translation agency: you read their brochure (the card), send the job (the message), get a
job number (the task id), and later the translated document (the artifact). You never see how they work inside.

**Task states.** A task moves through states the client can see:

| State | Meaning here |
|---|---|
| `SUBMITTED` | the agent accepted the message and gave the task an id |
| `WORKING` | the model is reading the receipt |
| `COMPLETED` | done: the task carries the `receipt_extraction` artifact |
| `FAILED` | the model failed or answered in the wrong shape (a fixed reason, never the model's words) |
| `REJECTED` | the request isn't what the skill takes (wrong parts, file type or size, malformed data); no model call |
| `CANCELED`, `INPUT_REQUIRED`, `AUTH_REQUIRED` | not used: a reading can't be stopped half-way, needs nothing more, and the key is checked before a task exists |

COMPLETED, FAILED, REJECTED and CANCELED are terminal: the task never changes again.

**A2A compared with MCP: why this is an agent and not a tool.** An MCP tool is a function the model calls: the
caller decides what to do, passes exact arguments, and gets a result immediately; the tool has no judgement and
holds no conversation (`add_expense(amount, category, ...)`). An A2A agent receives a *goal* and decides how to reach
it: here, it runs its own model with its own prompt and rules, checks its own answer, and reports through a task
that has a lifecycle (it can fail, be rejected, or, for slower agents, report progress and ask for input). The
client doesn't know or care that Gemini is inside: another agent with the same card could replace it. MCP connects a
model to *capabilities*; A2A connects an agent to *another agent*.

**Why the agent lives outside the monolith while the MCP module lives inside.** The MCP module is an adapter onto the
monolith's own data: its tools send commands and queries through the bus, act for the signed-in person, and touch
the database in the same unit of work. Moving it out would only add a network hop between a tool and the data it
exists to reach. The receipt agent needs none of that: it has no database, no bus and no notion of a person. What it
needs from the monolith (the receipt's bytes once its owner has been checked, the category names, today's date)
travels in the request. Outside, it gets its own lifecycle (start it, restart it, move it to a machine with more
capacity), and its slow model call can't tie up the backend's worker threads. And it's replaceable: any agent that
serves the same card and skill would do.

## Part 1: the agent on its own

**What was built** (`agents/receipt/`, D195):

| File | What it does |
|---|---|
| `contract.py` | The skill's id (`extract_receipt`), the request's data (`ReadingRequest`: today, categories, payment methods), the answer (`ReceiptExtraction`, D182's fields), the accepted media types and limits |
| `reader.py` | The model call, moved from D182: the same prompt, system instruction and checks; the categories and payment methods become the schema's enums |
| `executor.py` | The `AgentExecutor`: checks the message's two parts, moves the task SUBMITTED → WORKING → COMPLETED (or REJECTED / FAILED), and publishes the answer as a data artifact; reads in a worker thread |
| `task_store.py` | `ForgetfulTaskStore` (D198): tasks kept without their files' bytes, at most 20 |
| `card.py` | The Agent Card: name, JSON-RPC interface at the agent's URL, the skill, the bearer-key security scheme |
| `http.py` | `AgentGate` (D197): the key check (401), the size limit (411/413), `Cache-Control: no-store` |
| `settings.py`, `server.py`, `__main__.py` | Its settings (`RECEIPT_AGENT_KEY`, `RECEIPT_AGENT_PORT`), its composition root (`build_app(settings, llm)`), and the entry point |

Also: `a2a-sdk[http-server]==1.3.1` pinned in `requirements.txt`; `run-receipt-agent.ps1`; `setup_logging` takes
extra logger names; `.env.example`, configuration.md, security.md, architecture.md (a section on `agents/`, scans
4, 10 and 11) and AGENTS.md updated.

**The prompt, and the SDK as it is now.** The prompt names `message/send`: in A2A protocol 1.0 (a2a-sdk 1.x) the
JSON-RPC method is `SendMessage`, and the SDK builds a plain Starlette app from route helpers
(`create_agent_card_routes`, `create_jsonrpc_routes`) instead of the older `A2AStarletteApplication`. A file is a
`raw` part (bytes, sent as base64 in JSON) and structured data a `data` part (sources.md, section 32).

**Until Part 2, the monolith still reads receipts itself** (D182's `ReceiptExtractor`), so the chat keeps working.
The extraction prompt and schema exist twice until Part 2 deletes the monolith's copy.

**How it was checked:** 31 offline checks with a fake model, 3 live calls (2 read correctly, 1 hit a Gemini 503
and failed as designed). Details in D195.

### Try it

```powershell
# Once: make a key and put it in .env as RECEIPT_AGENT_KEY=<key>
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"

.\run.ps1                    # once, if requirements.txt changed: installs a2a-sdk (then stop it with Ctrl+C)
.\run-receipt-agent.ps1      # "Uvicorn running on http://127.0.0.1:9001"

# In another terminal: the card is open, everything else needs the key
curl.exe -s http://127.0.0.1:9001/.well-known/agent-card.json      # the card: name, skill extract_receipt, ...
curl.exe -s -X POST http://127.0.0.1:9001/ -d "{}"                  # {"error":"a valid bearer key is required"}
```
