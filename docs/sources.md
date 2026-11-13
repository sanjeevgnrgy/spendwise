# Sources: what the official docs and libraries say

The facts that Phases 14 to 17 are built on: where each came from, what it says, and what SpendWise does with it.
Earlier phases' doc facts are in [gemini.md](gemini.md) and the phase notes.

All checked on **2026-11-13**. Each fact is marked with where it came from:

- **Web:** official documentation or a specification, read online. The exact URLs are listed.
- **Package:** the source code or docstrings of the library **at the version pinned in `requirements.txt`**,
  under `.venv\Lib\site-packages\`. For the version we actually run, the code is the most reliable reference, because
  web docs can describe an older or newer release.
- **Observed:** seen in a live run or an offline experiment in this project.

Quotes are kept short. Follow the links for the full text. When a later phase depends on a doc fact, add it here.

---

## 1. Gemini Interactions API: streaming (Phase 14)

**Web:**
- https://aistudio.google.com/docs/interactions-overview (the old `ai.google.dev/gemini-api/docs/interactions` redirects here)
- https://aistudio.google.com/docs/streaming
- https://aistudio.google.com/docs/function-calling
- https://aistudio.google.com/docs/thought-signatures

What they say:
- **Event order:** `interaction.created`, then each step as `step.start` → one or more `step.delta` → `step.stop`, then
  `interaction.completed`. `interaction.status_update` can appear between steps; `error` is its own event. The raw
  stream ends with `data: [DONE]`. The docs advise to "log and skip any events you don't recognize".
- **Function calls:** "For function calls, the step includes the function name, id and empty arguments `{}`." The
  arguments then arrive as `arguments_delta` pieces of one JSON string: "You must accumulate these deltas to get the
  full arguments."
- **No steps at the end:** of `interaction.completed`, the streaming page says it "Does not include `steps` in the
  response." (A non-streamed response does have a `steps` array.)
- **Thoughts:** a `thought` step streams a `thought_signature` delta (field `signature`); `thought_summary` deltas come
  only when thinking summaries are enabled.
- **Stateless (`store=False`) function calling:** each request resends the `user_input`, then all model-generated steps
  "exactly as received" (including `thought` and `function_call`), then a `function_result` per call. `store=false`
  also rules out `previous_interaction_id`.
- **Automatic function calling** isn't available in the Interactions API for Python, so we run the loop ourselves.

Gaps and conflicts we found:
- No official example combines streaming, a manual function-calling loop and `store=False`. We combined the streaming
  page's pattern with the stateless function-calling pattern.
- The function-calling page's streaming sample uses `delta.type == "arguments"` and `delta.partial_arguments`. The
  streaming page uses `"arguments_delta"` and `delta.arguments`. We followed the streaming page, and the package agrees
  (below).

**Package** (google-genai 3.3.0, `google\genai\_gaos\`):
- `client.interactions.create(..., stream=True)` returns a `Stream`. You can loop over it, use it in a `with` block,
  and `close()` it, and it stops at the `[DONE]` line (`interactions.py`, `utils\eventstreaming.py`).
- The delta classes confirm the names: `ArgumentsDelta` has type `"arguments_delta"` and a field `arguments`;
  `TextDelta` is type `"text"`; `ThoughtSignatureDelta` has `signature` (`types\interactions\`).

**Observed:** a live streamed reply from `gemini-3.5-flash-lite` came as `interaction.created`, a `thought` step with a
`thought_signature` delta, a `model_output` step with two `text` deltas, then `interaction.completed` without steps.
A streamed function call (`arguments_delta`) hasn't been seen live yet.

**Used in:** `core/llm.py` `GeminiStream` rebuilds the steps from the deltas ([decisions.md](decisions.md) D102).

## 2. Gemini SDK: timeouts and retries (Phase 14 fix)

**Package** (google-genai 3.3.0):
- `HttpOptions.timeout` becomes the timeout of every HTTP request, and `retry_options.attempts` becomes
  `attempts - 1` retries (`_gaos\google_genai.py`, `_translate_retry_config`).
- The Interactions client retries these statuses by default: `["408", "409", "429", "5XX"]` (`_gaos\interactions.py`).
  `HttpRetryOptions.http_status_codes` **replaces** that list (`_gaos\utils\retries.py`, `status_codes_override`).
- Before a retry, if the response has a `retry-after-ms` header, the SDK sleeps exactly that long. `_get_sleep_interval`
  returns it directly, and the backoff cap only applies when there's no header. The request timeout doesn't cover this
  sleep.
- The SDK sends requests with its own HTTP library, `httpx2`, not `httpx`.

**Observed:** with the free-tier quota used up, Gemini answered **429** within a second. The SDK then waited in its
retry sleep for minutes, which looked like an endless "Thinking…". A mock 429 with `retry-after-ms: 600000` reproduced
it offline.

**Used in:** `core/llm.py` retries only `[500, 502, 503, 504]` (D108).

## 3. AG-UI protocol (Phases 14–15)

**Package** (ag-ui-protocol 1.0.0, `ag_ui\core`, `ag_ui\encoder`):
- **`RunAgentInput`:** `threadId`, `runId` and `messages` are required; `state`, `tools`, `context`, `forwardedProps`,
  `parentRunId` and `resume` are optional. Python uses snake_case names, and the JSON uses camelCase.
- **Encoding:** `EventEncoder` writes `data: <event.model_dump_json(by_alias=True)>` plus a blank line, with content type
  `text/event-stream`. Optional fields with no value are left out.
- **Event docstrings** (verbatim):
  - `TOOL_CALL_START`: "Opens a tool call. The arguments arrive as TOOL_CALL_ARGS events and the call closes with TOOL_CALL_END."
  - `TOOL_CALL_ARGS`: "Appends a fragment of a tool call's arguments."
  - `TOOL_CALL_END`: "Closes a tool call, meaning its arguments are complete."
  - `TOOL_CALL_RESULT`: "Carries what a tool returned. Mints a tool message rather than appending to an existing one,
    which is why it has its own messageId."
  - `STATE_SNAPSHOT`: "Replaces the agent state wholesale. Sent when a delta cannot express the change, or to
    resynchronise a consumer."
  - `STEP_STARTED`: "Opens a named step within a run, for producers whose frameworks have a step concept worth surfacing."
- AG-UI's `ToolMessage` has an `error` field, but `ToolCallResultEvent` doesn't. Every event has an optional `metadata`
  dictionary.

**Web:** the TypeScript client's event verifier,
https://raw.githubusercontent.com/ag-ui-protocol/ag-ui/main/sdks/typescript/packages/client/src/verify/verify.ts
(read in part; the file is long):
- **First event:** "First event must be 'RUN_STARTED'", where `RUN_ERROR` is also accepted first.
- **After `RUN_ERROR`:** "The run has already errored with 'RUN_ERROR'. No further events can be sent."
- **After `RUN_FINISHED`:** "The run has already finished with 'RUN_FINISHED'. Start a new run with 'RUN_STARTED'."
- **Tool calls during a text message:** no rule forbids it. `TOOL_CALL_START` only checks that the same tool-call id
  isn't already open.

**Used in:**
- `assistant/service.py` `agent_run()` (D101, D109, D112, D113). It always starts with `RUN_STARTED` and sends nothing
  after `RUN_ERROR`.
- `metadata: {"ok": ...}` on `TOOL_CALL_RESULT` is **our convention**, not part of AG-UI.

**Not read:** AG-UI's website docs; the package and the verifier were enough. Whether an empty `TEXT_MESSAGE_CONTENT`
delta is allowed couldn't be checked (the TypeScript schema file returned 404), so we simply never send an empty one.

## 4. FastAPI: Server-Sent Events (Phase 14)

**Package** (fastapi 0.162.5, `fastapi\sse.py`, `fastapi\routing.py`):
- `EventSourceResponse` "Works with **any HTTP method** (`GET`, `POST`, etc.), which makes it compatible with protocols
  like MCP that stream SSE over `POST`." You use it as `response_class=` on a route that `yield`s.
- `ServerSentEvent(data=...)` always JSON-encodes `data` (a string gets quotes); `raw_data` is sent as-is. We use
  `raw_data`, because AG-UI's JSON is already serialised.
- A **sync** generator is run with `iterate_in_threadpool`, one item at a time in a worker thread.
- While the generator is quiet, FastAPI sends `: ping` every 15 s (`_PING_INTERVAL = 15.0`), and it sets
  `Cache-Control: no-cache` and `X-Accel-Buffering: no`.
- The stream is attached to the request's exit stack, which "outlives the streaming response", so dependencies like
  the database session stay open until the stream ends.

**Not read:** FastAPI's website page on SSE; the code covers what we use.

**Used in:** `assistant/router.py` `POST /agent` (D101).

## 5. Browsers: `EventSource` vs `fetch()` (Phase 14)

**Web:**
- https://developer.mozilla.org/en-US/docs/Web/API/EventSource/EventSource
- https://html.spec.whatwg.org/multipage/server-sent-events.html

What they say:
- **No way to send a body:** the constructor's only option is `withCredentials`. The spec's `EventSourceInit` has just
  that one member, so there's no way to set a method, a body or headers.
- **Response rules:** the browser may send `Accept: text/event-stream`. The connection fails if the status isn't 200
  or the content type isn't `text/event-stream`.

**Used in:** `web/src/api.ts` `runAgent()` POSTs the run with `fetch()` and reads the body as a stream (D107).

## 6. MCP: tool annotations (Phase 15)

**Web:**
- The schema source for spec **2025-11-25**:
  https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2025-11-25/schema.ts
- The tools page: https://modelcontextprotocol.io/specification/2025-11-25/server/tools

What they say (verbatim):
- `readOnlyHint`: "If true, the tool does not modify its environment." "Default: false"
- `destructiveHint`: "If true, the tool may perform destructive updates to its environment. If false, the tool performs
  only additive updates." "Default: true" (meaningful only when `readOnlyHint == false`)
- `idempotentHint`: "Default: false"; `openWorldHint`: "Default: true"
- "Clients should never make tool use decisions based on ToolAnnotations received from untrusted servers." The tools
  page also says: "clients **MUST** consider tool annotations to be untrusted unless they come from trusted servers."

**Package** (mcp 2.3.0):
- `MCPServer.tool(annotations=...)` takes `mcp.types.ToolAnnotations`. Its Python fields are `read_only_hint`,
  `destructive_hint`, `idempotent_hint` and `open_world_hint`, sent as the camelCase names above.
- On the client side, each listed tool has `.annotations`.

**Used in:**
- `mcp/server.py` marks `list_expenses` and `get_summary` as read-only, `add_expense` as additive, and update/delete
  as destructive.
- `assistant/mcp_client.py` `changes_data()` treats a missing hint as "may change data", following the
  `readOnlyHint` default of false.
- Trusting the hints is fine because the server is our own (D111).

## 7. Uvicorn: auto-reload on Windows (troubleshooting)

**Package** (uvicorn 0.54.0, `uvicorn\supervisors\basereload.py`, `uvicorn\config.py`):
- On Windows, a reload sends the old worker a Ctrl+C event and then waits for it with `self.process.join()`, with no
  time limit.
- `timeout_graceful_shutdown` defaults to `None`, so a shutting-down worker waits for every open request to finish.

**Observed:** a request sleeping on a 429 kept the old worker alive for more than 10 minutes after a code change.
Meanwhile the server answered nothing, not even `/health`.

**Used in:** [troubleshooting.md](troubleshooting.md), "Every request stays pending after I changed backend code".

## 8. A2UI (Phase 16)

**Web** (spec **v1.0**, status "Current", last updated 8 Jun 2026; v0.9.x are "previous", v0.8 is "deprecated"):
- https://a2ui.org/specification/v1.0-a2ui/ (the protocol)
- https://a2ui.org/specification/v1.0-basic-catalog-implementation-guide/
- https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json (the basic catalog, read in full)
- https://raw.githubusercontent.com/a2ui-project/a2ui/main/specification/v1_0/json/agent_to_renderer.json (read in full)
- https://raw.githubusercontent.com/a2ui-project/a2ui/main/specification/v1_0/json/common_types.json (read in full)
- https://raw.githubusercontent.com/a2ui-project/a2ui/main/specification/versions.json

What they say:
- **Messages:** each message is `{"version": "1.0"}` plus exactly one of `createSurface`, `updateComponents`,
  `updateDataModel`, `deleteSurface`, `callRendererFunction`, `agentFunctionResponse`. `version` is required (const
  `"1.0"`), and no other keys are allowed.
- **`createSurface`:** only `surfaceId` is required. It may carry `catalogId`, `components` (at least 1), `dataModel`,
  `sendDataModel` and `metadata`. Creating a surface id that already exists is an error.
- **`updateComponents`** needs `surfaceId` and `components`; **`deleteSurface`** needs `surfaceId`.
- **Components:** a flat list where `"component": "Text"` names the type. `id` is required, and the prose asks for
  identifier-style ids (`user-card` is invalid). Children are id lists (`children`) or a single id (`child`). Rendering
  starts at the component with id `"root"`. Keys the catalog doesn't declare are rejected (`unevaluatedProperties: false`).
- **Values:** a plain JSON value is a literal. `{"@path": "/pointer"}` binds to the data model, and `{"@call": ...}`
  calls a function. Keys starting with `@` are reserved.
- **Basic catalog id:** `https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json`.
- **The components we use:**
  - Text: `text` (required), `variant` `caption` or `body` (default `body`). There are no heading levels, and the
    catalog says Text "Supports simple Markdown".
  - Card: one `child`.
  - Row and Column: `children`, plus `justify` (start, center, end, spaceBetween, spaceAround, spaceEvenly, stretch)
    and `align` (start, center, end, stretch).
  - List: `children`, plus `direction` vertical or horizontal.
  - Divider: `axis` horizontal or vertical.
  - Button: `child` and `action` (required), plus `variant` default, primary or borderless.
- **Actions:** an action is `{"event": {"name", "context"?}}` or `{"functionCall": ...}`. On a click, the renderer sends
  an `action` message back (with `name`, `surfaceId`, `sourceComponentId`, `timestamp` and `context`).
- **Why data, not code:** "A2UI expresses UI using _data_, not code", and functions "avoid sending raw executable code
  across the wire" (README and spec).
- **Other facts:** `a2ui-core` exists on PyPI (not used). The spec names AG-UI as a transport, but doesn't say how A2UI
  maps onto AG-UI events.

**Inputs, binding and actions (Phase 17):**
- **TextField:** `label` and `value` are required; `placeholder`; `variant` longText, number, shortText or obscured
  (default shortText); validation goes through `@checks`.
- **ChoicePicker:** `options` and `value` are required. `options` are `[{label, value}]`. `value` is a
  *DynamicStringList*: the guide says it "Binds to an array of strings in the data model". `variant` is
  multipleSelection or mutuallyExclusive (default mutuallyExclusive), and there's also `displayStyle` and
  `filterable`. **There is no `Select` component** in v1.0's basic catalog.
- **DateTimeInput:** `value` is required, ISO 8601 ("If not yet set, initialize with an empty string").
  `enableDate` and `enableTime` both default to **false**. Also `min`, `max` and `label`.
- **Two-way binding:** "input components modify the renderer-side data model immediately upon user interaction", and
  "Two-Way Binding is **local to the renderer**". Inputs "do **not** automatically trigger network requests". A
  missing path is created on write.
- **Initial and updated data:** `createSurface.dataModel` gives the starting data (applied before the components).
  `updateDataModel` takes `{surfaceId, path?, value}`; a missing path means `/`, and `null` removes a key.
- **Clicking a button:** the renderer "resolves any data bindings inside `action.event.context`" against the local
  data model when the button is clicked.
- **The `action` message** (renderer_to_agent.json): `name`, `surfaceId`, `sourceComponentId`, `timestamp`
  (date-time) and `context` are required; `userMessage` and `metadata` are optional. The envelope is `version` plus
  exactly one message key.
- **`sendDataModel`** (default false) makes the renderer attach the whole data model, as `a2uiRendererDataModel`
  metadata, to messages it sends to the agent that created the surface (not used).
- **Over AG-UI:** no official mapping. AG-UI's docs say it "natively supports" A2UI, with no event shapes, and A2UI's
  spec names AG-UI as a transport binding without details. SpendWise's choice is D124.
- More pages read: https://a2ui.org/concepts/messages/,
  https://raw.githubusercontent.com/a2ui-project/a2ui/main/specification/v1_0/json/renderer_to_agent.json,
  https://docs.ag-ui.com/introduction, https://docs.ag-ui.com/concepts/generative-ui-specs.md

**Package** (ag-ui-protocol 1.0.0): `CustomEvent` has `name` and `value`. Its docstring: "The protocol's extension point
for an application's own events. Anything a consumer does with one is outside the protocol."

**Used in:** `modules/assistant/a2ui/` (models and card) and `web/src/lib/a2ui.ts` with
`components/a2ui/a2ui-surface.tsx` (the renderer) (D116 to D118).

## 9. The `cn` npm package (correction, Phase 16)

**Package** (`web/node_modules/cn/package.json`, version 0.5.2):
- Description: "Fast, small, compiled class-name merging for Tailwind CSS. Drop-in replacement for clsx +
  tailwind-merge."
- Repository: `github.com/shadcn-ui/cn`.
- It was added to `web/package.json` in Phase 11 by shadcn's setup, and shadcn's components import it. This corrects
  D99 (D119).

---

## How to re-check a package fact

Library code lives in `.venv\Lib\site-packages\<package>\`. For example, to see the AG-UI event docstrings for the
installed version:

```powershell
.\.venv\Scripts\python.exe -c "import ag_ui.core as c; print(c.ToolCallEndEvent.__doc__)"
```

After upgrading a pinned package, re-check the facts above that cite it.
