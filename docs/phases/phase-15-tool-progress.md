# Phase 15: Tool progress

> **Later changes:** in Phase 16, `ToolFinished` also carries the tool's `name`, and a successful `add_expense` is
> followed by a `CUSTOM` "a2ui" event with an "Expense saved" card ([phase-16-a2ui-card.md](phase-16-a2ui-card.md)).
>
> **Refactor (after Phase 18):** chip labels come from the backend (`TOOL_CALL_START`'s `metadata.labels`);
> `dataVersion` is still AG-UI state, but pages refresh through TanStack Query. See
> [refactor-architecture.md](refactor-architecture.md).

**Goal:** while the assistant works, the chat panel shows each tool it uses as a small status chip ("Saving
expense…" → "Expense saved", or "Couldn't save expense"). The backend streams AG-UI tool events around every MCP call.
After a tool changes data, it also sends a `STATE_SNAPSHOT` with `{"dataVersion": n}`, and the pages reload when that
number changes. This replaces Phase 13's "guess from the tool names" refresh logic.

> **How it was checked:** offline, with no Gemini calls. The real app ran with a scripted fake Gemini and a
> throwaway seeded database, and the agent called the **real** MCP server. The script made a successful
> `add_expense` (the expense was really saved), a read-only `get_summary`, and a `delete_expense` that failed. The
> raw SSE stream was checked from Python, and the web app's `runAgent()` was run from Node. `POST /chat` still
> answered. `npm run build` passes. **Not yet tried with real Gemini or in a browser.**

## Design: why showing tool activity matters for trust

An assistant that can change your data asks for trust. If all you see is "Thinking…" and then "Done!", you can't tell
what it actually did. It may have looked up the right expense, saved it twice, or quietly failed and still sounded
confident. Showing each action **as it happens** turns a black box into something you can check:

- **You see what it's doing:** "Looking up expenses…" then "Saving expense…". The action is visible before the reply.
- **You can catch mistakes early:** "Updating expense" when you only asked a question is a red flag you notice
  straight away.
- **Failures are honest:** a red "Couldn't save expense" chip is evidence. You don't depend on the model admitting it
  in words.
- **The wording never overclaims:** a delete preview says "Waiting for your OK", not "Deleting".

**Analogy:** a food-delivery app that shows "Order received → Being prepared → Out for delivery" is easier to trust
than one that shows a spinner for 40 minutes. The food is the same; you just know what's happening.

## Design: the AG-UI events, around one MCP call

```
TOOL_CALL_START   {toolCallId, toolCallName: "add_expense"}      chip appears: "Saving expense…" (spinning)
TOOL_CALL_ARGS    {toolCallId, delta: "{\"amount\": \"250\", ...}"}   the arguments, as JSON text
TOOL_CALL_END     {toolCallId}                                     "the arguments are complete"
                  … the MCP call runs here …
TOOL_CALL_RESULT  {toolCallId, content: "...", metadata: {ok: true}} chip: "Expense saved" ✓ (or ✗ if ok is false)
STATE_SNAPSHOT    {snapshot: {dataVersion: 5}}                      only after a tool that changed data
```

- **`TOOL_CALL_END` is not "the tool has run".** In AG-UI it means "the arguments are complete" (the package's own
  docstring). What the tool returned is a separate event, `TOOL_CALL_RESULT`. So START, ARGS and END go out just
  before the MCP call, and RESULT goes out after it. The chip spins from START to RESULT.
- **Success or failure** goes in `metadata.ok`. `TOOL_CALL_RESULT` has no error field (AG-UI's `ToolMessage` does, but
  the event doesn't), and `metadata` is the slot every AG-UI event has for extra data. A failed chip shows the tool's
  error message when you hover over it.
- **Text before a tool is closed first.** If Gemini says "Let me check." and then calls a tool, that text message gets
  `TEXT_MESSAGE_END` before `TOOL_CALL_START`, and the answer after the tool comes as a new text message. The panel
  still shows one bubble per reply.
- **`STEP_STARTED` / `STEP_FINISHED` aren't sent.** The phase allowed them "if useful". Here the chips, the streaming
  text and "Thinking…" already show everything a user needs. A step is one round trip to Gemini, which means nothing
  to the user (decisions D113).

## Design: shared state and `dataVersion`

AG-UI lets an agent and its UI share a small piece of **state**. The client sends its copy with every run
(`RunAgentInput.state`), and the agent sends updates back as `STATE_SNAPSHOT` (the whole state) or `STATE_DELTA`
(a patch). SpendWise's state is one number:

1. The panel sends `state: {"dataVersion": 4}` with the run.
2. A tool that changed data succeeds, so the agent sends `STATE_SNAPSHOT {"dataVersion": 5}`.
3. The panel stores 5 in the data-sync context (Phase 13). The Dashboard and Expenses pages list `dataVersion` in
   their loading effects, so they fetch fresh data. The page updates while the assistant is still writing its reply.

**Who decides "this tool changed data"?** The MCP server that owns the tools, using **MCP tool annotations**:
`list_expenses` and `get_summary` are marked `read_only_hint=True`, and the other three aren't. The assistant's MCP
client reads the annotations along with the tool list. A successful call to a tool that isn't read-only counts as a
change. In Phase 13, the browser decided this from a hard-coded list of tool names. Now no tool names are repeated
anywhere outside the MCP server (the chip labels are just wording).

One trade-off: a `delete_expense` *preview* (`confirmed: false`) counts as a change, because the tool can delete. The
pages reload once for nothing, which is harmless (D111).

## What was built

| File | What |
|---|---|
| `modules/mcp/server.py` | Tool annotations: `READS_ONLY` for list/summary, `ADDS_DATA` for add, `CHANGES_DATA` for update/delete |
| `modules/assistant/mcp_client.py` | Keeps the full tool list (not just the Gemini declarations); `changes_data(name)` reads `read_only_hint` |
| `modules/assistant/agent.py` | `stream()` also yields `ToolStarted` before and `ToolFinished` (ok, text, changed_data) after each MCP call |
| `modules/assistant/service.py` | Maps them to `TOOL_CALL_START/ARGS/END/RESULT` and `STATE_SNAPSHOT`; closes open text before a tool; reads `dataVersion` from `run.state`. `RUN_FINISHED` no longer carries the tool calls |
| `web/src/api.ts` | The new event types, `AgentState`, and `runAgent(threadId, message, state, onEvent)`. `ToolCall` removed |
| `web/src/hooks/use-chat.ts` | Builds each reply's `tools` from the events; `STATE_SNAPSHOT` sets `dataVersion`; spinning chips turn red if the run fails. `changedData()` removed |
| `web/src/components/chat/tool-chip.tsx` | **New.** A chip per tool: spinner / tick / cross, with plain-English wording per tool |
| `web/src/components/chat/chat-message.tsx` | Chips above the reply text (tools run before the answer); no empty bubble before the text arrives |
| `web/src/components/chat/chat-panel.tsx` | "Thinking…" shows only while nothing else shows progress |
| `web/src/lib/data-sync.ts`, `components/data-sync-provider.tsx` | `setDataVersion(n)` replaces `notifyDataChanged()` |

`POST /chat` is unchanged: `agent.run()` waits for the end and ignores the tool events.

## Run it

`.\run.ps1` (restart it if it was already running: the assistant reads the tool list, now with annotations, only once)
and `cd web; npm run dev`. Open http://localhost:5173. Needs your Gemini key in `.env`.

## Verify it by hand

**1. In the app.** Open **Expenses** with the Assistant panel open, and send "Add 250 for lunch at Subway today, paid
by UPI". You should see:
- "Thinking…";
- then a chip **Saving expense…** with a spinner;
- then **✓ Expense saved**: the table gains the new row at that moment, before the reply finishes;
- then the reply text.

**2. Read-only questions don't refresh.** "How much did I spend on food this month?" shows **Adding up the month…** →
**✓ Added up the month**. The page doesn't reload.

**3. A delete preview is honest.** "Delete the Subway expense" shows **Looking up expenses** (✓), then **Checking the
expense…** → **✓ Waiting for your OK**, and the assistant asks you to confirm. Reply "yes": **Deleting expense…** →
**✓ Expense deleted**, and the row disappears.

**4. A failed tool.** Ask "Add 300 for a movie in the category Fun" (no such category). Expect a red **✗ Couldn't save
expense** chip. Hover over it to see the server's message (e.g. "Unknown category 'Fun'. Use one of: ..."). The
assistant then retries with a real category or asks you.

**5. The raw events.** As in Phase 14, from the project folder:

```powershell
'{"threadId":"demo15","runId":"run1","state":{"dataVersion":4},"messages":[{"id":"m1","role":"user","content":"Add 250 for lunch at Subway today, paid by UPI"}]}' | Set-Content -Encoding ascii run.json
curl.exe -N -X POST http://localhost:8000/agent -H "Content-Type: application/json" --data-binary "@run.json"
```

Expected, among the text events:

```
data: {"type":"TOOL_CALL_START","toolCallId":"…","toolCallName":"add_expense"}
data: {"type":"TOOL_CALL_ARGS","toolCallId":"…","delta":"{\"amount\": \"250\", \"category\": \"Food\", …}"}
data: {"type":"TOOL_CALL_END","toolCallId":"…"}
data: {"type":"TOOL_CALL_RESULT","metadata":{"ok":true},"messageId":"…","toolCallId":"…","content":"{\n  \"saved\": {…"}
data: {"type":"STATE_SNAPSHOT","snapshot":{"dataVersion":5}}
```

Delete `run.json` afterwards (and the expense, if you want).

## Design questions

**1. Why does `TOOL_CALL_END` go out *before* the MCP call, and which event says the call is done?**

<details><summary>Answer</summary>

In AG-UI, START/ARGS/END describe the call: END means "the arguments are complete", not "the tool has run". Once the
arguments are known, the call is fully described, so all three go out and then the tool runs. What the tool returned,
and so "it's done", is `TOOL_CALL_RESULT`. The chip spins from START until RESULT, and `metadata.ok` says tick or cross.
</details>

**2. The panel sends `state: {"dataVersion": 4}` with every run. What would go wrong if it didn't?**

<details><summary>Answer</summary>

The agent would start counting from 0 on every run. After the first change it would send `dataVersion: 1`. If the
panel already held 1 from an earlier run, the number wouldn't change, React would skip the update, and the pages
wouldn't reload. Sending the current state lets the agent continue from it, so each change produces a new number.
This is AG-UI's shared-state round trip.
</details>

**3. How does the backend know that `add_expense` changes data but `get_summary` doesn't, without a list of tool
names in the assistant?**

<details><summary>Answer</summary>

From MCP tool annotations. The MCP server declares `read_only_hint=True` on `list_expenses` and `get_summary`. The
assistant's MCP client receives the annotations with the tool list, and `changes_data(name)` treats anything not
marked read-only as a possible change. The MCP spec says to assume that when the hint is missing. The knowledge lives
with the tools, so a new tool only needs the right annotation.
</details>
