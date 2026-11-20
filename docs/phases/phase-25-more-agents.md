# Phase 25: More A2A agents

**Goal:** more specialist agents beside the receipt agent (a currency agent and an insights agent), every expense kept
in INR as well as its own currency, and the assistant choosing which agent to ask, including agents that need to ask
the person something before they can finish. Decisions: D201–D204 (Part 1).

**The owner's choices** (asked before building):

- **Three parts.** Part 1: a shared agent kit, the currency agent, and expenses stored with both amounts. Part 2: the
  insights agent on its own, with input-required. Part 3: the orchestrator (the Agent Card registry, a
  `delegate_to_agent` tool, asking the person and resuming the same task).
- **Conversion on the server, on every save** of an expense not in INR (REST, MCP, the assistant): the original amount
  and currency, the INR amount, the rate and its date; totals in INR across currencies; if the currency agent can't be
  asked, the save is refused with a clear message.
- **What the insights agent will get** (Part 2): each expense's date, INR amount, category, merchant and payment
  method for the period asked; no notes, ids or anything about the person. The model never chooses it.
- Up to 5 live Gemini calls (Parts 2 and 3; the currency agent uses no model).

## The ideas (Part 1)

**A specialist agent without a model.** The currency agent has no Gemini inside. What makes it an A2A agent is the
contract, not the intelligence: it's an independent service that publishes an Agent Card, offers a skill, and turns
each request into a task with a state and an artifact. Any client that reads A2A can discover and use it, and the
model-based agents coming in Parts 2 and 3 talk to it the same way. Behind its skill is a `RateProvider` interface: a
mock with made-up rates now, a real exchange-rate API later, a change in one file.

**Why the conversion isn't the model's job.** A rate is a fact, and saving an expense is a rule. If the model had to
remember to convert before calling `add_expense`, an expense from an MCP client or the REST API would skip it, and a
model that forgot would put a dollar amount into a rupee total. So the server converts, at the one door every save
goes through (`ExpenseRecorder`), before the command: the bus's unit of work never waits on the network. The currency
agent is asked only what one unit of a currency was worth on a day; it never sees the amount, the merchant or the
person, and the backend does the multiplication with the same rounding rule the agent uses.

**One port for every agent.** The backend now has two clients of A2A agents (the receipt reader and the exchange
rates), and Part 3 adds a third. So the A2A details (fetching the card, checking it's the agent we expect, sending the
key, reading the task) live once, in `infrastructure/a2a/`, behind `core/agents.RemoteAgents`, like the model and the
sign-in provider. Each module keeps its own small adapter that says what to send and checks what comes back.

## Part 1: the currency agent, and both amounts

**What was built:**

| Where | What |
|---|---|
| `backend/app/core/agents.py` | `RemoteAgents`, `AgentTask`, `TaskOutcome`, the parts, `AgentUnavailableError` (D201) |
| `backend/app/infrastructure/a2a/` | `A2AAgents`: the A2A SDK, card check, key, one `SendMessage` per task (D201) |
| `assistant/receipt_agent/agent_reader.py` | the receipt reader on the port (was `a2a_client.py`; same checks) |
| `agents/agent_kit/` | the gate, the task store, the task helpers, the settings rules, the app builder (D202) |
| `agents/currency/` | the currency agent on :9003: contract (data or text), `rates.py` (`RateProvider`, `MockRateProvider`), executor, card (D203) |
| `core/money.py` | `BASE_CURRENCY` and `convert_minor`, the one rounding rule |
| `expenses/conversion/` | the `ExchangeRates` port and `CurrencyAgentRates` (asks for 1 unit, checks the answer) |
| `expenses/application/record_expense.py` | `ExpenseRecorder`: rate first, then the command (D204) |
| `expenses/domain/base_amount.py` | the INR amount, rate and date for a row |
| migration `0008_base_amounts` | the three columns, INR rows filled in |
| summaries, trend, MCP | totals in INR across currencies; `get_summary` without `currency`; `amount_in_inr` on every expense |
| web | `ExpenseMoney` ("$4.00 / ≈ ₹338.00", the rate in its title), the table sorted by the INR amount, `formatRate` |
| `run-agent.ps1` | starts any agent: `.\run-agent.ps1 receipt`, `.\run-agent.ps1 currency` |

**How it was checked:** the receipt flow gave the same 32 results as in Phase 24 through the new port; 35 checks of
the currency agent and both amounts through the HTTP API and MCP (D204); the expense API and MCP recorded before and
after (only the intended changes); migration 0008 up, down and up on a copy of the database; and the real currency
agent process asked over a socket by the backend's own adapter. No live Gemini call was needed.

### Try it

```powershell
# .env: CURRENCY_AGENT_KEY=<32+ random characters>  (python -c "import secrets; print(secrets.token_urlsafe(32))")
.\run.ps1                       # terminal 1: the backend (applies migration 0008)
.\run-agent.ps1 currency        # terminal 2: the currency agent on :9003
cd web; npm run dev             # terminal 3: http://localhost:5173
```

Add an expense in dollars (in the chat: "add a 4 dollar coffee at Blue Tokai today, paid by card", or through the
API with `"currency": "USD"`). The Expenses page shows "$4.00" with "≈ ₹338.00" under it (mock rate 84.5), and the
Dashboard's total includes ₹338.00. Stop the currency agent and try again: the save is refused with "Currency
conversion isn't available right now"; an expense in INR still saves.
