# Refactor: SOLID, testability and scalability (after the CQRS refactor)

**Goal:** a code review against single responsibility and the other SOLID principles, clean code, no god files,
testability and scalability, then the fixes, with no change to what the app does. Two reviews (backend and web) found
nine issues each; every one was fixed or deliberately documented. Decisions: D172–D174. Findings and their
resolutions: [architecture-review.md](../architecture-review.md#5-the-solid-review).

> **How it was verified**
> - **Backend, behaviour:** 22 scenarios through the HTTP API (the insight card; delete, Approve and Cancel; Approve
>   from another thread, after an edit and twice; the form and Save; `/chat`; `/parse`; errors; every REST read), with
>   a scripted fake model plugged in at the model port, recorded before and after: every AG-UI event, response, call
>   to the model (instructions, tools, history), plus the MCP tool listing and the OpenAPI document. **Identical.**
> - **Backend, edges:** the old and new agent loop side by side for paths the scenarios don't reach (tools
>   unreachable, the 5-step cap, an empty answer); the old and new Gemini adapter fed the same SDK events (15 cases).
> - **Migrations:** 0004 up, down, up and `alembic check` on a copy of the real database.
> - **Web:** `tsc -b`, `oxlint` and `npm run build`; then the real app in headless Edge against the backend with the
>   fake model: both pages render with data, the chat panel loads on demand, the insight card draws its chart, and a
>   delete is approved from its card and carried out.

## Design: what each principle changed

**Single responsibility.** A unit should have one reason to change. `assistant/agent.py` had four: the system prompt,
which tools the web panel offers, the loop itself, and Approve/Cancel (which never calls the model). They're now
`prompts.py`, `surfaces.py`, `agent.py` and `decisions.py`, with running a tool in `tool_runs.py`. In the web app,
`use-chat.ts` did seven jobs; the event handling is now pure functions (`transcript.ts`, `run-progress.ts`) and the
hook only wires them.

**Open/closed.** Adding something shouldn't mean editing a switch. The MCP server registers tools from a table
(`TOOL_REGISTRARS`); the A2UI renderer looks components up in `CATALOGS`; the web app's refresh rule is a table
(`STALE_AFTER`) the compiler checks for every data scope.

**Interface segregation.** `/parse` only asks for JSON and the agent only streams with tools, so each depends on its
own small protocol (`StructuredOutputModel`, `ToolCallingModel`), and a fake for either needs one method.

**Dependency inversion.** The `rich_ui` flag that switched behaviour in three places became a `Surface` the use case
passes in (`WebPanel` or `TextChat`). The composition root now builds everything replaceable (clock, engine, model,
tools) and `create_app(services)` serves whatever it's given.

## What was built

**Backend**

| Where | What |
|---|---|
| `assistant/` | `prompts.py`, `surfaces.py`, `tool_runs.py`, `decisions.py`, `agui_request.py`; `agent.py` is `Agent.run` (117 lines of code, was 272) |
| `assistant/parse.py`, `tools.py` | `ExpenseParser` (its schema built once); `McpExpenseTools` picks in-process or remote once |
| `core/llm/` | the port split in two; `gemini_wire.py` (pure translation and stream assembly) apart from the SDK calls |
| `core/db.py`, `bootstrap.py`, `main.py` | `create_db_engine(url)`; `build(clock, llm, tools, engine)`; `create_app(services)` |
| `mcp/` | `create_server` from 185 lines to 7: `read_tools.py`, `write_tools.py`, `resources.py`, `views.py`, `tool_support.py` |
| `migrations/versions/0004_conversation_turn_index.py` | an index on (thread_id, turn); the old thread_id index dropped |
| contracts | `conversations.THREAD_NOT_FOUND`; `mcp.AUTHORIZATION_HEADER` and `BEARER_SCHEME`, shared by the endpoint and its client |

**Web**

| Where | What |
|---|---|
| `features/assistant/model/`, `api/` | `use-chat.ts` wires `transcript.ts`, `run-progress.ts`, `use-agent-run.ts`; `sse.ts` and `agent-events.ts` |
| `features/assistant/components/` | the composer and the transcript apart (typing no longer redraws the cards); `lazy-chat-panel.tsx` |
| `features/assistant/a2ui/` | `catalogs.ts` registry, `basic-components.tsx`, pure `actions.ts` and `insight-data.ts` |
| `features/expenses/` | the table split into columns, sort button, toolbar and editor hook; `use-expense-draft.ts`, `labeled-field.tsx` |
| `shared/lib/` | `query-status.ts` (the Dashboard's retry rule), `lazy-with-retry.ts` |
| `app/query-client.ts` | `STALE_AFTER` and `refreshAfter` |

**Fixed along the way:** saving two rows quickly no longer loses the first row's toast, and each row shows its own
saving state; ids no longer need `crypto.randomUUID` (missing on plain-http LAN addresses); a page or the chat panel
whose code failed to load shows the problem, and **Try again** loads it, without reloading the page.

**Then reviewed again.** Two more independent reviews read the finished result against the code. They found no
behaviour regression and confirmed the new abstractions. They found:
- one real bug: the first retry design looped, retrying a failed load forever behind a blank area;
- the engine seam only half done: migrations could only target `DATABASE_URL`, and in-memory engines weren't shared
  across threads;
- a pre-existing edge case: Approve could report an error after its delete was saved;
- an app built as a side effect of importing `main.py`;
- misplaced comments and one duplicated parse.

All were fixed, and the failed-load case was checked in a browser with the chunk blocked.

## Run it

Nothing changes: `.\run.ps1` (it applies migration 0004), then `npm run dev` in `web/`. In the browser's network tab,
the Expenses page, the Dashboard and the chat panel now load their own files when first opened.

## Verify it by hand

1. Open the app: the Dashboard appears as before. Open **Expenses**: a short pause the first time, while its code
   loads, then the table.
2. Open the Assistant and type: the cards already in the conversation don't flicker or redraw.
3. Edit two rows' amounts and save them quickly one after the other: each shows its own "Expense updated".
4. Stop the dev server, click another page, start it again, and press **Try again**: the page loads.

## Design questions

**1. `agent.run` took a `rich_ui: bool`. What's wrong with a flag argument, and what replaced it?**

<details><summary>Answer</summary>

A flag means the function does two things, and every place that differs needs an `if rich_ui` (three, here: the
prompt, the tool list and the delete handling). Adding a third kind of client would add a third branch everywhere. A
`Surface` object carries the differences instead: its prompt rules, the tools it offers and the calls it handles
itself. The loop asks the surface and never branches, and a new surface is a new class.
</details>

**2. How could the refactor be shown to change nothing, with no automated tests?**

<details><summary>Answer</summary>

By recording behaviour at the edges, before and after. A fake model plugged in at the model port answers by script,
and fixed scenarios run through the real HTTP API on a copy of the database. Everything observable is written down:
every event, every response, and every argument the app hands the model. The two recordings were identical. This
works only because the seams exist: the fake reaches the app through `bootstrap.build(llm=...)`, not by patching code.
</details>

**3. Why does each feature's `index.ts` make its page lazy, and not `app/pages.tsx`?**

<details><summary>Answer</summary>

`app/` also imports each feature's index for other things (its query keys, for the refresh rule). A module that's
imported normally anywhere stays in the main bundle, so a `lazy()` in `app/` would split nothing. The boundary has to
be where the page is exported.
</details>

> **Later changes:** the backend's modules were then reorganised inside, with no change in behaviour (checked with
> the same recorded scenarios): commands and queries became vertical slices (one file per message, holding the
> message and its handler), and the assistant's files moved into folders by role, so `agent.py`, `surfaces.py`,
> `prompts.py` and `tool_runs.py` are now in `assistant/agent/`, and `decisions.py` in `assistant/application/`.
> MCP tools are one file each in `mcp/tools/`. See
> [D175](../decisions.md#d175-vertical-slices-inside-modules-folders-by-role).
