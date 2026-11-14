# Phase 8: Memory

> **Later changes (refactor after Phase 18):** threads moved to a new **conversations** module (`conversation_message`) and are
> stored as provider-neutral messages, not raw Gemini steps; a migration converted the old ones. `GET
> /api/v1/threads/{id}`. See [refactor-architecture.md](refactor-architecture.md).

**Goal:** `/chat` remembers the conversation. Each conversation is a **thread** with a `thread_id`. Its messages
(the user's, the model's, tool calls and their results) are stored in a `ChatMessage` table owned by the assistant
module, and the recent ones are sent with every new message so follow-ups like *"actually it was 300"* work.
`GET /threads/{id}` shows a conversation.

## Design

**Why the model forgets without this.** A model has no memory between requests. Each call to Gemini is complete on
its own: the model sees exactly what's in that request and nothing else. Phase 7's agent *looked* like it
remembered within one message, but only because the loop resent the growing history at every step. When the next
`/chat` request arrived, it started from an empty history, so "actually it was 300" meant nothing. (Google *can* keep
conversations server-side, but we set `store=False` for privacy, so remembering is our job.)

**Analogy:** phoning a helpful expert who forgets each call the moment you hang up. To continue yesterday's discussion,
you read them the notes from earlier calls first. The `ChatMessage` table is that notebook.

**The cost trade-off of long history:**
- **Tokens are paid for on every request.** Each message resends the history, and within one message the agent
  loop resends it at *every step*. So a long conversation is paid for again and again: the total grows much faster
  than the conversation itself.
- **It's slower,** because there's more for the model to read.
- **There's a size limit** (the context window), and long, mostly irrelevant history can distract the model.
- **So:** send only the **last N turns** (`MAX_HISTORY_TURNS = 10`). Older turns stay stored (and visible in
  `GET /threads`), but the model no longer sees them. A turn is one user message plus everything up to the reply, and
  trimming always cuts between whole turns, so a tool call is never separated from its result.
- **Watch it happen:** each step now logs `tokens: N in, M out`, and the input number grows as a thread gets longer.

## What was built

| File | What |
|---|---|
| `modules/assistant/models.py` | **New.** `ChatMessage` table: `thread_id`, `turn`, `kind`, `content` (JSON), `created_at`. Private to the assistant module |
| `modules/assistant/repository.py` | **New.** `add_turn`, `last_turn`, `messages(from_turn=...)` |
| `modules/assistant/service.py` | `chat(session, message, thread_id)`: start or continue a thread, load the last 10 turns, save the new turn. `get_thread()` |
| `modules/assistant/agent.py` | `run(..., history)` sends earlier history + this turn; returns every step of the turn (`AgentResult.steps`); logs token usage |
| `modules/assistant/schemas.py` | `ChatRequest.thread_id`, `ChatResponse.thread_id`, `ThreadRead`, `ThreadMessage` |
| `modules/assistant/router.py` | `GET /threads/{thread_id}` |

**Each row is one step, stored exactly as Gemini sent or received it,** so it can be resent unchanged:

```python
class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    thread_id: str = Field(index=True, max_length=32)   # one conversation; the server picks a random UUID
    turn: int                                            # 1, 2, 3...: lets us keep only the last N turns
    kind: str                                            # user_input, thought, function_call, function_result, model_output
    content: dict[str, Any] = Field(sa_type=JSON)        # the step itself
    created_at: datetime
```

**Starting or continuing a thread** (`service.py`):

```python
def chat(session, message, thread_id=None):
    if thread_id is None:
        thread_id, turn, history = uuid4().hex, 1, []            # a new conversation
    else:
        last = repository.last_turn(session, thread_id)
        if last is None:
            raise NotFoundError(f"Thread {thread_id} not found")  # a typo shouldn't silently start a new one
        turn = last + 1
        rows = repository.messages(session, thread_id, from_turn=turn - MAX_HISTORY_TURNS)
        history = [row.content for row in rows]
    result = agent.run(session, message, date.today(), history)
    repository.add_turn(session, thread_id, turn, result.steps)  # the whole turn, in one commit
```

**What a stored turn looks like.** For "I spent 250 on lunch at Subway today, paid by UPI":
`user_input` → (`thought`) → `function_call add_expense(...)` → `function_result {...id: 11...}` → `model_output "Recorded..."`.
When the next message says "actually it was 300", Gemini sees this turn, including the result with **id 11**, so it
can call `update_expense(expense_id=11, amount="300")`.

**`GET /threads/{id}`** returns the readable conversation: turn, kind, text and time. Gemini's internal `thought`
steps are stored (they're part of the history that gets resent) but left out of this view.

## Run it

From the project folder: `.\run.ps1`. No new packages. The `chatmessage` table is created automatically at startup
(existing tables and data are untouched).

## Verify it by hand

In `/docs`:

1. **POST /chat** `{"message": "I spent 250 on lunch at Subway today, paid by UPI"}` → 200. Copy the
   **`thread_id`** from the reply (32 hex characters).
2. **POST /chat** `{"message": "Actually it was 300", "thread_id": "<paste it>"}` → it should call
   **`update_expense`** with the Subway expense's id and `"amount": "300"`, and say so. Without the `thread_id`
   it would have no idea what "it" means; try that too.
3. **GET /threads/{thread_id}** → both turns: `user_input`, `function_call`, `function_result`, `model_output` for
   turn 1, then the same pattern for turn 2.
4. **POST /chat** with `"thread_id": "nope"` → **404** `Thread nope not found`.

In the terminal, compare the `tokens: ... in` line of the first message with the second's: the second is bigger,
because it carries turn 1.

Gemini's wording and exact tool choices vary between runs. These steps weren't run against real Gemini while
building this phase. What was checked:
- **With a scripted stand-in for Gemini** (since removed, see [decisions.md](../decisions.md) D64):
  - a new thread stores the whole turn,
  - a follow-up sends the earlier conversation,
  - no `thread_id` means a fresh start,
  - with N = 2, only the last 2 turns are sent but all are kept,
  - an unknown thread is a 404 (and Gemini isn't asked),
  - `thought` steps are resent but hidden from the view.
- **With the real server on a throwaway database:** it starts, creates the `chatmessage` table next to the existing
  ones, lists `/chat` and `/threads/{thread_id}`, and returns 404 for an unknown thread.

## Design questions

**1. Phase 7's agent remembered things across the steps of one message, but not across two `/chat` calls. Why?**

<details><summary>Answer</summary>

Gemini itself never remembers anything; each request stands alone (and with `store=False`, Google keeps nothing).
Within one message, *our loop* kept a growing `history` list in memory and resent it at every step, so it looked
like memory. That list was thrown away when the request ended, so the next `/chat` started from just the new message.
Phase 8 saves the list to the `ChatMessage` table and loads it back for the next message in the same thread.
</details>

**2. Why not just send the entire thread every time? What do we give up by sending only the last 10 turns?**

<details><summary>Answer</summary>

Every token of history is paid for on every request, and again on every step of the agent loop. A long thread gets
more expensive and slower with each message, can hit the model's context limit, and old details can distract the
model. With only the last 10 turns, cost and latency stay bounded. What we give up: the model can't see anything
older than that, so a reference to something said 15 turns ago won't be understood. (Fixes for later: summarising old
turns, or looking things up with tools, which ours already can for expense data.)
</details>

**3. Why is the history trimmed by whole turns, rather than "the last 30 steps"?**

<details><summary>Answer</summary>

A step-count cut could land in the middle of a turn. For example, it could keep a `function_result` but drop the
`function_call` it answers, or start the history with a model step instead of a user message. That history is
inconsistent, and the API may reject it or the model may misread it. A turn always starts with the user's message
and ends with the model's answer, so cutting between turns keeps every call paired with its result.
</details>
