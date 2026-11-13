# Phase 7: Function calling chat

**Goal:** `POST /chat {"message": "..."}` lets you talk to SpendWise in plain language. Gemini decides
which tools to call (add, list, summarise, update, delete expenses), we run them, and it answers.
The reply comes back with a list of the tools it used, and every step is logged to the console.

## Concepts

**Function calling.** We tell Gemini about some functions it may use: their names, what they do, and what
arguments they take. Gemini **never runs anything itself**. When it decides a function would help, it answers
with a *request*: "please call `add_expense` with these arguments". Our code runs the function and sends the
result back. Gemini then either asks for another call, or answers the user in text.

**The agent loop, step by step:**

1. **Start the conversation:** `history = [the user's message]`.
2. **Ask Gemini**, sending the history, the tool declarations and the system instruction.
3. **Look at the answer:**
   - **Text only?** That's the final reply. **Stop.**
   - **One or more function calls?** Carry on.
4. **Add Gemini's steps (its thoughts and calls) to the history, unchanged.** We use `store=False`, so Google
   remembers nothing: every request must carry the whole conversation so far.
5. **Run each call** through the matching Python function, and append a `function_result` with its output
   (or the error, marked `is_error`).
6. **Go back to step 2**, at most **5** times.

**Analogy:** a manager (Gemini) and an assistant with access to the filing cabinet (our tools). The manager
can't touch the cabinet; they say "fetch me all Food receipts from November". The assistant fetches them and
hands them back, and the manager reads them and either asks for something else or gives you the answer.

**Why cap the steps:**
- A confused model can loop: list, list again, try to add, fail, retry...
- Every step is a paid round trip (free-tier quota), and the user's request stays open the whole time.
- The cap guarantees an answer within a bounded time and cost. On hitting it, `/chat` says
  *"that took too many steps"* instead of hanging.

Five is plenty for real requests. "Delete the Subway expense" takes three: find it, ask about deleting it, answer.

## What was built

| File | What |
|---|---|
| `modules/assistant/tools.py` | **New.** `add_expense`, `list_expenses`, `get_summary`, `update_expense`, `delete_expense`, thin wrappers over the `expenses` (and `categories`) **public interfaces** |
| `modules/assistant/agent.py` | **New.** The loop (`run`), tool declarations built from the signatures, the system instruction, tool execution with logging |
| `modules/assistant/schemas.py` | `ChatRequest`, `ToolCall` (name, arguments, ok), `ChatResponse` (reply, tool_calls) |
| `modules/assistant/router.py`, `service.py` | `POST /chat` → `service.chat()` → `agent.run()` |
| `core/llm.py` | `ask_gemini_with_tools(history, tools, system_instruction, thinking_level)` |
| `core/logging.py` | **New.** Prints SpendWise's own INFO logs (`spendwise.*`) to the console |
| `tests/assistant/test_agent.py` | **New.** 9 tests with a **scripted** fake Gemini (see below) |

**A tool is a normal Python function.** The docstring tells the model *when* to call it; each argument's
`Annotated` description tells it *what* to pass:

```python
def add_expense(
    session: Session,
    amount: Annotated[str, "Amount as a plain number string, e.g. '450.50'."],
    category: Annotated[str, "Category name, exactly as in the category list."],
    ...
    currency: Annotated[str, "ISO currency code. INR unless the user says otherwise."] = "INR",
) -> dict[str, Any]:
    """Record a new expense. Only call this when you know the amount, category, merchant, date and
    payment method; if any of them is missing, ask the user instead of guessing."""
    created = expenses.create_expense(session, expenses.ExpenseCreate(...))   # the public service
```

`agent.py` turns each signature into Gemini's declaration (`{"type": "function", "name", "description",
"parameters"}`), so the declaration can never drift away from the code. `session` is left out, because we pass it,
not the model.

**The loop** (`agent.py`, shortened):

```python
history = [{"type": "user_input", "content": [{"type": "text", "text": message}]}]
for step in range(1, MAX_STEPS + 1):
    interaction = llm.ask_gemini_with_tools(history, DECLARATIONS, instruction, THINKING_LEVEL)
    calls = [s for s in interaction.steps if s.type == "function_call"]
    if not calls:
        return ChatResponse(reply=interaction.output_text, tool_calls=tool_calls)   # done
    history += [s.model_dump() for s in interaction.steps]          # Gemini's steps, unchanged
    for call in calls:
        result, ok = _run_tool(session, call.name, call.arguments)   # logged to the console
        history.append({"type": "function_result", "name": call.name, "call_id": call.id,
                        "is_error": not ok, "result": [{"type": "text", "text": json.dumps(result)}]})
return ChatResponse(reply="Sorry, that took too many steps ...", tool_calls=tool_calls)
```

**Safety, following the project rules:**
- **Confirm before deletes.** `delete_expense` deletes nothing unless `confirmed=true`. The system instruction says
  to call it first with `confirmed=false`, show the user what would go, and ask.
- **Tool results are data, never instructions:** this is stated in the system instruction. A note saying
  "ignore your rules" stays just a note.
- **Errors go back to the model, not up as crashes.** An unknown category, a bad date, a missing expense, an unknown
  tool or wrong arguments become `{"error": ...}` with `is_error: true`. Gemini can then fix its call or explain the
  problem to the user.

**The system instruction** says who the bot is, today's date, INR as the default currency, the category list, to
ask when something is missing, the delete rule, and to keep replies short.

## What testing it live showed

| Message | Steps | Tools called | Reply (shortened) |
|---|---|---|---|
| "I spent 250 on lunch at Subway today, paid by UPI" | 2 | `add_expense` | "Recorded ₹250.00 for Food at Subway today (2026-11-13), paid via UPI." |
| "How much did I spend on food this month?" | 2 | `get_summary` **and** `list_expenses` (in parallel, one step) | "You've spent ₹1,820.90 on Food this month across 3 expenses ..." (correct) |
| "Delete the Subway expense" | 3 | `list_expenses`, then `delete_expense(confirmed=false)` | "Are you sure you want to delete this expense? Subway, ₹250.00, ..." (nothing deleted) |

At first the delete message **timed out twice**. Gemini spent 40–60+ seconds per step thinking, which was over the
30 s limit from Phase 6. Two fixes followed:
- **`thinking_level="low"` for the agent.** Recording and looking up expenses is simple bookkeeping. Afterwards
  the same message took **9 s in total**.
- **The per-attempt timeout went from 30 s to 60 s,** because a function-calling step can legitimately take 20–30 s.

## Run it

From the project folder: `.\run.ps1`. No new packages. Watch the terminal while you chat; you'll see lines like:

```
14:16:22 INFO    spendwise.agent: user: Delete the Subway expense
14:16:22 INFO    spendwise.agent: step 1/5: asking Gemini
14:16:27 INFO    spendwise.agent:   tool call: list_expenses({"merchant": "Subway"})
14:16:27 INFO    spendwise.agent:     -> {"count": 1, "expenses": [{"id": 11, "amount": "250.00", ...}]}
14:16:27 INFO    spendwise.agent: step 2/5: asking Gemini
14:16:29 INFO    spendwise.agent:   tool call: delete_expense({"confirmed": false, "expense_id": 11})
14:16:29 INFO    spendwise.agent:     -> {"deleted": false, "needs_confirmation": true, ...}
14:16:29 INFO    spendwise.agent: step 3/5: asking Gemini
14:16:31 INFO    spendwise.agent: step 3: Gemini answered in text, done
```

## Test it by hand

In `/docs`, open **POST /chat** and click **Try it out**. Try these one at a time:

1. `{"message": "I spent 250 on lunch at Subway today, paid by UPI"}` → **200**. The reply confirms it, and
   `tool_calls` shows `add_expense` with `"ok": true`. **This one really saves**: check `GET /expenses`.
2. `{"message": "How much did I spend on food this month?"}` → a total, using `get_summary` and/or `list_expenses`.
3. `{"message": "Coffee at Starbucks"}` (no amount, no payment method) → a question back, such as
   "How much was it, and how did you pay?", with **no** tool call.
4. `{"message": "Delete the Subway expense"}` → it asks you to confirm; the expense is still there.
5. `{"message": "Yes, delete the Subway expense of ₹250 from today"}` → `delete_expense` with `confirmed: true`.

**/chat doesn't remember earlier messages yet:** each message is a fresh conversation. So the follow-up in step 5
must say everything again; "yes" on its own won't work. Conversation threads come in a later phase.

Wording varies between runs; which tools get called, and in what order, can vary a little too.

Automated: `python -m pytest` → **56 passed** (9 new). The agent tests use a **scripted** fake Gemini, which returns
"call add_expense", then "here's my answer", so each path is checked exactly: a normal run, hitting the 5-step cap,
a failing tool, an unknown tool, wrong arguments, delete confirmation, logging, and `POST /chat`.

## Check your understanding

**1. Walk through what happens, step by step, for "How much did I spend on food this month?" in the live run above.**

<details><summary>Answer</summary>

1. `history` holds just the user's message.
2. **Step 1:** we send the history, the 5 tool declarations and the system instruction (which includes today's
   date, so "this month" means November 2026).
3. Gemini answers with **two function calls**: `get_summary({"month": "2026-11"})` and
   `list_expenses({"category": "Food", "start_date": "2026-11-01", "end_date": "2026-11-30"})`.
4. We append Gemini's steps to the history unchanged, run both tools (logging each), and append a
   `function_result` for each, matched by `call_id`.
5. **Step 2:** we send the longer history. Gemini now has the data, answers in text ("₹1,820.90 ... across 3
   expenses"), and the loop ends. `/chat` returns that reply plus both tool calls.
</details>

**2. Why cap the loop at 5 steps? What happens when the cap is hit?**

<details><summary>Answer</summary>

Without a cap, a confused model could keep calling tools forever. Each call costs a round trip, quota and time,
and the user's request would never finish. The cap bounds the time and cost of any single message. At the cap,
the loop stops and `/chat` returns "Sorry, that took too many steps ... try a simpler request", together with
the tool calls that did happen, so you can see what it was attempting.
</details>

**3. Why do the tools call `expenses.create_expense()` and friends instead of the expenses repository directly?**

<details><summary>Answer</summary>

The service is where the business rules and conversions live: amount > 0, the category must exist, rupees → paise.
Going through it means the agent gets exactly the same protection as the REST API. A repository call would skip
every rule, and it would break the module boundary (the repository isn't part of `expenses`' public interface),
so the architecture test would fail.
</details>
