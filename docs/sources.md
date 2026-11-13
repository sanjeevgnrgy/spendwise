# Sources: what the official docs and libraries say

The facts that Phases 14 to 18 and the architecture refactor are built on: where each came from, what it says, and what SpendWise does with it.
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
In Phase 18, live streamed function calls (`get_summary`, `delete_expense`) were rebuilt correctly from their
`arguments_delta` pieces.

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
- **How tool arguments are read** (found by the code review, then confirmed through the protocol):
  - The SDK reads a tool argument whose type isn't exactly `str` as JSON first (`pre_parse_json`). So the text `"null"`
    becomes `None`, and `"true"` becomes `True`.
  - Pydantic's default (lax) `bool` also accepts `"yes"`, `"on"` and `1`. `Field(strict=True)` limits it to real
    booleans (D133, D134).
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

**Custom catalogs (Phase 18):**
- **The id:** a catalog's `catalogId` is "an arbitrary string ID and not a resolvable URI". It's conventionally a
  URI, with a version in the path for breaking changes.
- **Self-contained:** a `$ref` into another catalog "makes the catalog invalid".
- **No extending:** a custom catalog can't extend the basic one. Catalogs are combined on one surface: a component
  names its own with `"@catalogId"`.
- **Resolution order** (verbatim): "1. Explicit Component/Function-Level Catalog ID", then "Surface Default
  `catalogId`", else a resolution error, with "**no fallback**" to the renderer's declared catalogs.
- **Renderers** advertise `supportedCatalogIds` (in `a2uiRendererCapabilities`). An unresolvable component "is not
  rendered".
- **No official chart:** the basic catalog has no chart; A2UI's `@a2ui/catalog-vegachart` is "Not published yet".
- **Buttons** may carry a `userMessage` (DynamicString), sent along with the `action`.
- Pages read: https://a2ui.org/concepts/catalogs/, https://a2ui.org/guides/defining-a-catalog/,
  https://raw.githubusercontent.com/a2ui-project/a2ui/main/specification/v1_0/json/catalog_definition.json

**Package** (shadcn's `web/src/components/ui/chart.tsx`): `ChartStyle` writes each config key and colour into a
`<style>` tag with `dangerouslySetInnerHTML` (`--color-${key}: ${color};`). That's why the A2UI Chart uses a fixed
config (D127).

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

## 10. MCP Python SDK 2.3.0: in-process clients, structured output, HTTP security (refactor)

**Package** (`.venv\Lib\site-packages\mcp\`):
- `client/client.py`, class `Client`: "Pass a URL string (Streamable HTTP), a `StdioServerParameters` ..., any
  `Transport`, or - in tests - a `Server` or `MCPServer` instance to connect to it in-process." With `mode="auto"`, "for
  an in-process `Server`/`MCPServer` it dispatches directly without JSON-RPC framing". SpendWise's `McpExpenseTools`
  passes the server object by default, or a URL with an `httpx2.AsyncClient` carrying the bearer token
  (`streamable_http_client(url, http_client=...)`: "To configure headers, authentication ... create an
  httpx2.AsyncClient and pass it here").
- `server/mcpserver/server.py`, `tool(structured_output=None)`: "If None, auto-detects based on the function's return
  type annotation". A tool annotated `-> ExpenseSaved` (a Pydantic model) gets an `outputSchema`, and its result
  arrives as `CallToolResult.structured_content` (`mcp_types/_types.py`).
- `server/lowlevel/server.py`, `streamable_http_app()`: "Auto-enable DNS rebinding protection for localhost": when no
  `transport_security` is given and `host` is `127.0.0.1` (the default), only Host `127.0.0.1:*`, `localhost:*`,
  `[::1]:*` and the matching `http://` Origins are accepted. **Observed:** a bad Host gets 421, a bad Origin 403.
- `server/mcpserver/utilities/func_metadata.py`: tool arguments are validated by an `ArgModelBase` Pydantic model with
  the default config, so **undeclared arguments are ignored**. **Observed:** `delete_expense(expense_id=1,
  confirmed=false)` against a tool without `confirmed` deleted the expense. Hence the required, strict `confirmed`
  (D145).
- The SDK has no hook for a simple shared-secret check (its auth is OAuth), so `/mcp/` is wrapped in a small ASGI
  middleware (`mcp/http.py`, D150).

**Web:** the MCP spec's Streamable HTTP security warning
(https://modelcontextprotocol.io/specification/2025-06-18/basic/transports):
- "Servers MUST validate the Origin header on all incoming connections to prevent DNS rebinding attacks"
- "When running locally, servers SHOULD bind only to localhost (127.0.0.1) rather than all network interfaces"
- "Servers SHOULD implement proper authentication for all connections"

---

## 11. AG-UI in TypeScript: `@ag-ui/core` 1.0.4 (refactor)

**Package** (`web/node_modules/@ag-ui/core`):
- README: "`@ag-ui/core` delivers the strongly-typed building blocks ... Runtime validation – schemas catch malformed
  payloads early." The validators live at `@ag-ui/core/schemas`; zod is an optional peer dependency ("the main entry
  never loads it").
- `dist/index.d.ts` exports the `EventType` enum (also at runtime) and the `Event` union; `dist/schemas.d.ts` exports
  `EventSchemas` (a zod discriminated union). Each event schema keeps `metadata` (`z.ZodOptional<...Record<string,
  any>>`), so our `metadata.ok` and `metadata.labels` survive validation.

**Package** (`.venv\...\ag_ui\_generated\models.py`): every event's `BaseEvent` has `metadata: Optional[Metadata]`,
"Extra information attached to this event". `TOOL_CALL_START` carries the chip labels there (D157).

---

## 12. Alembic 1.20.1 (refactor)

**Web:**
- https://alembic.sqlalchemy.org/en/latest/batch.html: "The SQLite database presents a challenge to migration tools in
  that it has almost no support for the ALTER statement". Batch mode copies the table into a new one instead. "To
  support rendering of migration commands in batch mode for autogenerate, configure the
  EnvironmentContext.configure.render_as_batch flag in env.py". It's "safe to use in all cases, as the
  Operations.batch_alter_table() directive by default only takes place for SQLite".
- Running commands from code: `alembic.command.upgrade(config, "head")`.
  https://alembic.sqlalchemy.org/en/latest/api/commands.html
- Checking the version: `MigrationContext.configure(connection).get_current_revision()` and
  `ScriptDirectory.from_config(config).get_current_head()`.
  https://alembic.sqlalchemy.org/en/latest/api/runtime.html

**Package:** `alembic/templates/generic/script.py.mako` was copied as `backend/migrations/script.py.mako`.

---

## 13. RFC 9457: problem details for HTTP APIs (refactor)

**Web:** https://www.rfc-editor.org/rfc/rfc9457
- "When serialized in a JSON document, that format is identified with the "application/problem+json" media type."
  Members: `type`, `title`, `status`, `detail`, `instance`; extension members (our `errors` list) are allowed.
- "The "type" member is a JSON string containing a URI reference that identifies the problem type." "The type URI is
  allowed to be a non-resolvable URI" (its example is a `tag:` URI), "However, resolvable type URIs are encouraged".
  SpendWise uses non-resolvable `urn:spendwise:problem:<kind>` names, as it has no public documentation site to point
  them at yet (D149).

---

## 14. TanStack Query v5 (refactor)

**Web:**
- https://tanstack.com/query/v5/docs/framework/react/guides/query-cancellation: "TanStack Query provides each query
  function with an AbortSignal instance. When a query becomes out-of-date or inactive, this signal will become
  aborted." Cancelling only works if the signal is passed on (we pass it to openapi-fetch and `fetch`).
- https://tanstack.com/query/v5/docs/framework/react/guides/query-invalidation: an invalidated query "is marked as
  stale", and "If the query is currently being rendered via useQuery or related hooks, it will also be refetched in
  the background".
- `placeholderData: keepPreviousData` keeps showing the last results while new ones load:
  https://tanstack.com/query/v5/docs/framework/react/guides/paginated-queries
- Typing `meta` app-wide by declaring it on the `Register` interface:
  https://tanstack.com/query/v5/docs/framework/react/typescript

**Package** (`web/node_modules/@tanstack/query-core`, 5.107.1, its `.d.ts`): a mutation's `meta` can be "read back from
`mutationFn`, callbacks and cache-level handlers. Defaults to `Record<string, unknown>`; declare `mutationMeta` on
Register to narrow it." That's how `app/query-client.ts` reads `meta.changes` in one `MutationCache` handler, and why
`shared/config/data-scopes.ts` declares `mutationMeta` (a misspelt scope is a compile error) (D168).

---

## 15. openapi-typescript 7.13.0 and openapi-fetch 0.17.0 (refactor)

**Web:** https://openapi-ts.dev/cli and https://openapi-ts.dev/openapi-fetch/
- `--enum-values` (default false): "Export enum values as arrays." We use `paymentMethodValues`.
- `--default-non-nullable` (default true): "Treat schema objects with default values as non-nullable (with the
  exception of parameters)". That made `currency` required in `CreateExpense`, though the server fills it in, so
  `gen:api` passes `--default-non-nullable false`.
- openapi-fetch's calls resolve to `{ data, error, response }`, typed from the same `paths`.

**Observed:** `npm view openapi-typescript@7.13.0 peerDependencies` is `typescript: ^5.x` (no release supports
TypeScript 7 yet), so it can't be a dev dependency here; `gen:api` runs it pinned through `npx` (D160).

---

## 16. oxlint 1.93 and React (refactor)

**Observed:** oxlint's `no-restricted-imports` accepts ESLint's `patterns` with `group` and `message`, and `overrides`
apply it per folder. Patterns match the import text (gitignore-style), so `../../**` from one folder deep means
"leaves the feature". Each rule was checked with a deliberate violation.

**Web:**
- Catching rendering errors needs a class component's `componentDidCatch` / `getDerivedStateFromError`: "There is no
  direct equivalent for componentDidCatch in function components yet."
  https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary
- `useSyncExternalStore` subscribes to a source outside React (here, a media query) without setState in an effect:
  https://react.dev/reference/react/useSyncExternalStore

---

## 17. SQLAlchemy 2.1.8 and SQLite transactions (code review)

**Package:** `sqlalchemy/dialects/sqlite/base.py`, section "Transactions with SQLite and the sqlite3 driver" (the
pysqlite docs' "Serializable isolation / Savepoints / Transactional DDL" section now points there).
- Python's `sqlite3` driver by default uses a "legacy transaction mode" that "does not "begin" a transaction
  automatically", "skips it for DDL (e.g. CREATE TABLE etc.) statements", and "Statements such as SAVEPOINT are also
  skipped".
- So: "**Incorrect support for transactional DDL**", and "**Incorrect behavior for SAVEPOINT**".
- The fix for all Python versions: "Using SQLAlchemy to emit BEGIN in lieu of SQLite's transaction control": set the
  driver connection's `isolation_level = None` in a `connect` event, and emit `BEGIN` in a `begin` event.
  `core/db.py` does exactly that, so `begin_nested()` (SAVEPOINT) and transactional migrations work (D163).

**Web:** the same recipe in the 2.0 docs:
https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#serializable-isolation-savepoints-transactional-ddl

**Observed:** before the fix, a migration that failed half-way left the table renamed but not converted; after it,
the same failure left the database exactly as it was, and a failing nested command undid only its own row.

---

## 18. RFC 9110: the authentication scheme is case-insensitive (code review)

**Web:** https://www.rfc-editor.org/rfc/rfc9110#section-11.1: HTTP "uses a case-insensitive token to identify the
authentication scheme". So `bearer abc` is as valid as `Bearer abc`; the MCP endpoint's check accepts both (D165).

---

## 19. Starlette 1.10.0: the order of middleware (code review)

**Package:** `starlette/applications.py`.
- `add_middleware()` does `self.user_middleware.insert(0, ...)`: the middleware added **last** is the **outermost**.
- "`ServerErrorMiddleware` is added as the very outermost middleware", and "`ExceptionMiddleware` is added as the very
  innermost". An unexpected error reaching `ServerErrorMiddleware` has already left CORS, so its 500 carries no CORS
  headers and the browser can't read it.

So `main.py` adds `UnexpectedErrorMiddleware` first and CORS after: CORS wraps it, and a 500 problem is readable
(D165).

**Observed:** a route that raised a plain exception answered 500 with `access-control-allow-origin` set and a problem
body.

---

## How to re-check a package fact

Library code lives in `.venv\Lib\site-packages\<package>\`. For example, to see the AG-UI event docstrings for the
installed version:

```powershell
.\.venv\Scripts\python.exe -c "import ag_ui.core as c; print(c.ToolCallEndEvent.__doc__)"
```

After upgrading a pinned package, re-check the facts above that cite it.
