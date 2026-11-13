# Phase 14: AG-UI streaming

**Goal:** the assistant's reply appears in the chat panel **as Gemini writes it**, instead of all at once after a
pause. A new endpoint, `POST /agent`, accepts an **AG-UI** run input (`threadId`, `runId`, `messages`) and streams
**AG-UI events** over **Server-Sent Events (SSE)**: `RUN_STARTED`, `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`
(one per piece of text from Gemini's streaming API), `TEXT_MESSAGE_END`, `RUN_FINISHED`, or `RUN_ERROR` on failure.
`POST /chat` keeps working as before.

> **How it was checked:** offline, with no Gemini calls. A scripted fake Gemini stream, built from the SDK's own event
> types, was fed through the real app twice: once with FastAPI's TestClient, and once on a real uvicorn server with
> the web app's `runAgent()` reading it from Node. The checks covered the streamed pieces, the rebuilt history, a
> Gemini error mid-stream, a missing user message, `/chat` and the MCP-unavailable reply. `npm run build` passes.
> **Not yet run against real Gemini or in a browser.**
>
> **Live check (gemini-3.5-flash-lite):** a real streamed reply arrived as `interaction.created`, a `thought` step with its
> `thought_signature` delta, a `model_output` step with two `text` deltas, then `interaction.completed` without steps,
> exactly the shape `GeminiStream` expects. A streamed *function call* (`arguments_delta`) hasn't been seen live yet.
>
> **Found while testing:** the chat hung forever. Live probes showed the free-tier quota was used up (Gemini answered
> 429), and the SDK silently slept before retrying. Fixed by never retrying a 429 ([decisions.md](../decisions.md) D108).

## Concept 1: normal HTTP vs Server-Sent Events

**Normal HTTP (`POST /chat`):** the browser sends a request and the server works out the **whole** answer. That
includes every Gemini step and tool call, often 5 to 20 seconds. Then it sends one complete response, and the
browser parses it in one go. Until then, the user sees only "Thinking…".

**SSE (`POST /agent`):** still **one ordinary HTTP request**, but the server answers with
`Content-Type: text/event-stream` and **keeps the response open**, writing small messages (events) whenever it has
something new. The browser reads each event as it arrives. The format is plain text:

```
data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"7f3…","delta":"You spent "}

data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"7f3…","delta":"₹1,240 on food"}

: ping

```

Each event is one or more `data:` lines followed by a **blank line**. A line starting with `:` is a comment. FastAPI
sends `: ping` every 15 s while nothing else is happening, so proxies don't think the connection died.

**Analogy:** normal HTTP is a restaurant that brings your order only when every dish is ready. SSE is the same order,
but each dish comes out as soon as it's cooked. Same table, same order, one waiter. You just start eating sooner.

Things that follow from this:

- **The status code goes first.** HTTP sends the status (`200`) and headers before the body. Once the stream has
  started, the server can't change its mind and send a `502`. So failures **during** a run travel **inside** the
  stream, as a `RUN_ERROR` event. A malformed body (e.g. no `threadId`) is still rejected with a normal `422` before
  any streaming starts.
- **One direction only.** SSE is server → browser. The browser talks to the server by sending a new request (the next
  message). That's all a chat needs. **WebSockets** are two-way, but they're a different protocol and more work to run;
  we don't need them.
- **Not `EventSource`.** Browsers have a built-in SSE client, `EventSource`, but it can only send **GET** requests,
  with no body. An AG-UI run is a **POST** with a JSON body, so the web app uses `fetch()` and reads `response.body` as
  a stream.
- **Buffering is the enemy.** Anything between the server and the browser that waits for the whole response
  (compression, some proxies) would hide the streaming. FastAPI sends `Cache-Control: no-cache` and
  `X-Accel-Buffering: no` for this reason.

## Concept 2: AG-UI and what each event means

**AG-UI** (Agent–User Interaction protocol) is an open standard for how an **agent backend** talks to a **user
interface**. It fixes the request shape (`RunAgentInput`) and a vocabulary of event types, so any AG-UI frontend can
talk to any AG-UI agent. MCP standardised *agent ↔ tools* in Phase 9; AG-UI standardises *agent ↔ UI*. One request is
one **run**. One conversation is one **thread**.

| Event | Meaning | What the chat panel does |
|---|---|---|
| `RUN_STARTED` (`threadId`, `runId`) | "I've accepted this run and started working." Always the first event. | Nothing yet; "Thinking…" is already showing |
| `TEXT_MESSAGE_START` (`messageId`, `role: "assistant"`) | A new message from the assistant begins. Every piece that follows names this `messageId`. | Adds an empty assistant bubble |
| `TEXT_MESSAGE_CONTENT` (`messageId`, `delta`) | The next piece of that message's text, in order. One per piece Gemini streams. | Appends `delta` to the bubble: the reply "types itself" |
| `TEXT_MESSAGE_END` (`messageId`) | That message is complete. | Nothing extra (a richer UI might render Markdown now) |
| `RUN_FINISHED` (`threadId`, `runId`, `result`) | The run succeeded and nothing more will come. `result` is free-form; SpendWise puts `{"toolCalls": [...]}` there. | Shows the tool badges; refreshes the page if data changed (Phase 13) |
| `RUN_ERROR` (`message`, `code`) | The run failed. Also final: no `RUN_FINISHED` follows. | Keeps any text already shown, adds a red bubble with `message` |

A successful run is always `RUN_STARTED → TEXT_MESSAGE_START → TEXT_MESSAGE_CONTENT × n → TEXT_MESSAGE_END →
RUN_FINISHED`. AG-UI has more event types that SpendWise doesn't send yet:

- `TOOL_CALL_START` / `TOOL_CALL_ARGS` / `TOOL_CALL_END` / `TOOL_CALL_RESULT`, to show "Adding expense…" live;
- `STATE_SNAPSHOT` / `STATE_DELTA`, for shared state;
- `STEP_STARTED` / `STEP_FINISHED`;
- `REASONING_*`;
- `CUSTOM`.

The Python types come from the official **`ag-ui-protocol`** package (`from ag_ui.core import RunStartedEvent, ...`).
They're Pydantic models with camelCase JSON names. The JSON is the same as the package's own `EventEncoder`
produces.

## Concept 3: streaming from Gemini, with tools in the loop

The agent still runs the Phase 7 loop: ask Gemini, run the tools it asks for, ask again, until it answers in text.
The difference is that every Gemini step is now requested with `stream=True`. The Interactions API then sends a
sequence of events:

```
interaction.created
step.start  (index 0, a "thought" step)       step.delta (thought_signature)   step.stop
step.start  (index 1, a "function_call" step: name, id, arguments {})
step.delta  (arguments_delta '{"amount": "250", ')   step.delta (arguments_delta '"merchant": "Subway"}')   step.stop
interaction.completed   (status, token usage; no steps)
```

…or, for the final answer, `step.start` of a `model_output` step followed by `text` deltas. That gives two jobs:

1. **Forward the text.** Every `text` delta is passed straight on to the browser as a `TEXT_MESSAGE_CONTENT`. Thoughts
   arrive as other delta types (`thought_signature`, `thought_summary`), so they never reach the user.
2. **Rebuild the steps.** The next request has to resend every step **exactly as received**, including the thought
   signature, which Gemini needs to carry on its reasoning after a tool call. But `interaction.completed` does **not**
   include the steps when streaming. So `GeminiStream` in `core/llm.py` puts them back together from the pieces:
   - it keeps each `step.start` under its index;
   - it joins the deltas for that index;
   - it then puts the joined text into `content`, the JSON into `arguments` (parsed once complete), or the signature
     into `signature`.

```python
response = llm.stream_gemini_with_tools(history, declarations, instruction, THINKING_LEVEL)
for text in response:      # text pieces, as Gemini writes them
    yield text             # -> TEXT_MESSAGE_CONTENT
turn += response.steps     # afterwards: the complete steps, as a non-streamed response has them
```

If Gemini says something before calling a tool ("Let me check."), the user sees it straight away. The text after the
tool call continues the same bubble, starting a new paragraph.

## What was built

| File | What |
|---|---|
| `core/llm.py` | `stream_gemini_with_tools()` returns a `GeminiStream`: loop over it for text, then read `.steps` / `.usage`. Replaces `ask_gemini_with_tools()` |
| `modules/assistant/agent.py` | `stream()`: the agent loop, yielding text pieces and finally the `AgentResult`. `run()` (for `/chat`) just waits for the end, so both endpoints share one loop |
| `modules/assistant/service.py` | `agent_run()`: turns the agent's output into AG-UI events, loads/saves the thread, and turns failures into `RUN_ERROR`. `_history()` is shared with `chat()` |
| `modules/assistant/router.py` | `POST /agent` with FastAPI's `EventSourceResponse`; each AG-UI event is sent as one SSE `data:` line |
| `modules/assistant/schemas.py` | `MAX_MESSAGE_LENGTH`, `MAX_THREAD_ID_LENGTH`, shared by `/chat` and `/agent` |
| `requirements.txt` | `ag-ui-protocol==1.0.0` |
| `web/src/api.ts` | `runAgent(threadId, message, onEvent)`: POSTs the run, reads the SSE stream, calls `onEvent` per event. `AgentEvent` type, `newId()`. `sendChatMessage` removed |
| `web/src/hooks/use-chat.ts` | Uses `runAgent`: creates the bubble on `TEXT_MESSAGE_START`, appends each `delta`, adds badges and refreshes on `RUN_FINISHED` |
| `web/src/components/chat/chat-panel.tsx` | "Thinking…" only until the first text arrives |

**How the route stays safe.** `POST /agent` is a plain (sync) generator:

```python
@router.post("/agent", response_class=EventSourceResponse)
def agent_run(body: RunAgentInput, session: SessionDep) -> Iterator[ServerSentEvent]:
    for event in service.agent_run(session, body):
        yield ServerSentEvent(raw_data=event.model_dump_json(by_alias=True))
```

FastAPI runs a sync generator in a worker thread, one item at a time. That keeps the Phase 10 rule: the agent calls
this same app's `/mcp`, so nothing may block the event loop, or it would wait for itself forever (D74). FastAPI also
keeps the database session open until the stream ends, and adds the keep-alive pings.

**Threads, the AG-UI way.** With `/chat`, the server invents the `thread_id`. With AG-UI, the **client** names the
thread: the web app makes a random 32-character id when a conversation starts. So `/agent` treats an unknown
`threadId` as a new conversation, where `/chat` answers 404. The run input's `messages` could carry the whole
conversation, but the server only reads the **newest user message**. It already stores the thread's history,
including Gemini's thoughts and tool results, which the browser never sees. The turn is saved only when the run
succeeds, as with `/chat`.

## Run it

`.\run.ps1` from the project folder (it installs the new `ag-ui-protocol` requirement automatically), and
`cd web; npm run dev`. Open http://localhost:5173. Needs your Gemini key in `.env`.

## Test it by hand

**1. See the raw stream.** In a second PowerShell window, from the project folder:

```powershell
'{"threadId":"demo1","runId":"run1","messages":[{"id":"m1","role":"user","content":"How much did I spend on food this month?"}]}' | Set-Content -Encoding ascii run.json
curl.exe -N -i -X POST http://localhost:8000/agent -H "Content-Type: application/json" --data-binary "@run.json"
```

(`-N` turns off curl's buffering, so events print as they arrive; `-i` shows the headers. The body goes in a file
because Windows PowerShell 5.1 mangles quotes in arguments to programs.) Expected: `HTTP/1.1 200 OK`,
`content-type: text/event-stream; charset=utf-8`, `cache-control: no-cache`, then:

```
data: {"type":"RUN_STARTED","threadId":"demo1","runId":"run1"}

data: {"type":"TEXT_MESSAGE_START","messageId":"…","role":"assistant"}

data: {"type":"TEXT_MESSAGE_CONTENT","messageId":"…","delta":"You've spent …"}

…more TEXT_MESSAGE_CONTENT…

data: {"type":"TEXT_MESSAGE_END","messageId":"…"}

data: {"type":"RUN_FINISHED","threadId":"demo1","runId":"run1","result":{"toolCalls":[{"name":"get_summary","arguments":{…},"ok":true}]}}
```

There's a pause after `RUN_STARTED` while Gemini calls the tool, and a `: ping` line if that takes over 15 s.
How many `TEXT_MESSAGE_CONTENT` events a reply has is up to Gemini: a short answer may come in one or two pieces.
Delete `run.json` afterwards.

**2. In the app.** Open the Assistant panel and ask "What were my 3 biggest expenses this month?" You see
"Thinking…" while the tools run, then the reply grows in its bubble, and the tool badges appear when it finishes.
Adding an expense still refreshes the page (Phase 13).

**3. Memory still works.** Follow up with "Delete the biggest one", then "yes". The same `threadId` is sent, so the
server continues the thread. `GET /threads/<the id>` shows it; the id is in the request payload in the browser's
Network tab.

**4. See the stream in the browser.** DevTools → Network → the `agent` request: its `Content-Type` is
`text/event-stream`, and the request stays open (pending) for the whole run, while the bubble fills in.

**5. Errors.** Send a body without `threadId` with curl: a normal **422**, no stream. Stop the backend and send a
message in the app: a red "Can't reach the SpendWise API" bubble. If Gemini fails mid-run, you get a `RUN_ERROR`
event (the panel keeps any text already shown and adds a red bubble).

**6. `/chat` is unchanged.** In `/docs`, `POST /chat` returns the same JSON as before. (Swagger UI can call
`/agent` too, but it shows the stream only after the run has ended. Use curl to watch it live.)

## Check your understanding

**1. Gemini fails halfway through a reply. `/chat` answers 502 for that; why does `/agent` send a `RUN_ERROR` event
with status 200 instead?**

<details><summary>Answer</summary>

HTTP sends the status line and headers before the body. `/agent` has already sent `200` and several events when the
failure happens, so the status can't be changed any more. The only way left to tell the client is inside the stream:
`RUN_ERROR` is AG-UI's "this run failed" event, and it's final. Problems found before streaming starts (a body
without `threadId`) still get a normal `422`.
</details>

**2. Gemini's streamed `interaction.completed` event doesn't include the steps. Why does the agent need them, and how
does it get them?**

<details><summary>Answer</summary>

With `store=False`, every request must resend the whole conversation, including Gemini's own steps **exactly as
received**: its thought (with the signature it needs to continue reasoning after a tool call) and its function calls.
`GeminiStream` rebuilds them from the stream. It keeps each `step.start` under its `index` and joins that index's
deltas. Then it puts the result in the right place: text into `content`, `arguments_delta` pieces parsed as JSON
into `arguments`, the `thought_signature` into `signature`.
</details>

**3. Browsers have a built-in SSE client, `EventSource`. Why does the web app read the stream with `fetch()` instead?**

<details><summary>Answer</summary>

`EventSource` can only make GET requests, and it can't send a body. An AG-UI run is a POST whose JSON body carries
`threadId`, `runId` and `messages`. `fetch()` can POST and expose the response body as a stream. The app then splits
it on blank lines and parses each `data:` line itself.
</details>
