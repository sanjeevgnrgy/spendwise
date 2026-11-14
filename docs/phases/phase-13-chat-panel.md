# Phase 13: Chat panel

> **Later changes:** in Phase 14 the panel switched from `POST /chat` to the streaming `POST /agent` (AG-UI over SSE).
> `sendChatMessage` and `ChatReply` were replaced by `runAgent()`. The reply now appears as it's written, the tool calls
> arrive with `RUN_FINISHED`, and the browser picks the thread id. See
> [phase-14-agui-streaming.md](phase-14-agui-streaming.md). In Phase 15, the tool badges became live status chips, and
> the refresh no longer guesses from tool names (`changedData()` is gone): the agent sends a new `dataVersion` in a
> `STATE_SNAPSHOT`, and `setDataVersion` replaced `notifyDataChanged` ([phase-15-tool-progress.md](phase-15-tool-progress.md)).
> **Correction (Phase 16):** the "shadcn bug" described below wasn't one. `cn` is a real npm package (shadcn's class-name
> merger) that all the shadcn components import; see [decisions.md](../decisions.md) D119.
> This page records Phase 13 as it was built.
>
> **Refactor (after Phase 18):** the conversation lives in the assistant feature's `AssistantProvider`. The
> data-version context is gone: the assistant reports changes, and the app invalidates the expenses and Dashboard
> queries. See [refactor-architecture.md](refactor-architecture.md).

**Goal:** an Assistant chat panel available on every page: a resizable side panel on desktop, a Sheet on mobile.
It keeps a `thread_id`, sends messages to `POST /chat`, shows replies with the tools used, and refreshes the current
page when the assistant changes data.

> **How it was checked:** `npm run build` (type-check and bundle) passes, and the backend compiles. The panel hasn't
> been used in a browser yet, and no live chat calls were made while building this phase.

## Design: how the panel and pages stay in sync without a page reload

The chat panel and the current page are **siblings** inside the layout: neither contains the other, so they can't
pass props to each other directly. The usual React answer is to put the shared piece of state in a **common
ancestor** and let both read it. Here that state is one number, a **data version**, held in a React **context** that
wraps the whole app:

1. The Dashboard and Expenses pages read `dataVersion` and list it in their data-loading `useEffect` dependencies.
2. When a chat reply shows a tool actually **changed** data (`add_expense`, `update_expense`, or `delete_expense`
   with `confirmed: true`), the panel calls `notifyDataChanged()`, which adds 1 to the number.
3. React re-renders everything that reads the context. The page's effect sees a new `dataVersion` and runs again,
   fetching fresh data from the API, while you stay on the same page with the chat still open.

**Analogy:** a "last updated" counter on an office noticeboard. Whoever changes the files bumps the counter; everyone
who cares glances at it and re-reads the files when it changes. Nobody has to phone everybody else.

This only works because both sides go through the **same backend**: the assistant changed the database via MCP, and
the page simply asks the API again. The browser never has to work out *what* changed.

## What was built

| File | What |
|---|---|
| `lib/data-sync.ts`, `components/data-sync-provider.tsx` | **New.** The shared `dataVersion` + `notifyDataChanged()` context, provided in `main.tsx` |
| `hooks/use-chat.ts` | **New.** The conversation as a custom hook: messages, `thread_id`, sending, `send()`, `reset()`, and the "did data change?" check |
| `components/chat/chat-panel.tsx` | **New.** Header (New conversation, Close), ScrollArea of messages, suggestions when empty, Textarea + Send |
| `components/chat/chat-message.tsx` | **New.** A message bubble, plus shadcn Badges for the tools used (red when a tool call failed) |
| `components/app-layout.tsx` | An Assistant button in the top bar; a resizable chat panel on desktop, a Sheet on mobile |
| `pages/dashboard/dashboard-page.tsx`, `pages/expenses/expenses-page.tsx` | `dataVersion` added to their loading effects |
| `api.ts` | `sendChatMessage(message, threadId)` and the `ChatReply` / `ToolCall` types |
| `components/ui/resizable.tsx`, `scroll-area.tsx`, `textarea.tsx` | Added with `npx shadcn add` |
| `backend/.../assistant/agent.py` | The system instruction now asks for plain-text replies (no Markdown) |

**Where the conversation lives.** `useChat()` is called in `AppLayout`, which stays on screen across pages, not
in the panel. Closing the panel unmounts it, and changing pages swaps the page, but the conversation and its
`thread_id` survive both, so the next message continues the same server-side thread (Phase 8 memory).

```ts
async function send(text: string) {
  add({ role: "user", text })
  const reply = await sendChatMessage(text, threadId ?? undefined)
  setThreadId(reply.thread_id)                       // continue this thread next time
  add({ role: "assistant", text: reply.reply, toolCalls: reply.tool_calls })
  if (changedData(reply.tool_calls)) notifyDataChanged()
}
```

**The layout** (`app-layout.tsx`):
- **Desktop:** a `ResizablePanelGroup` with the page panel, and, when open, a drag handle and the chat panel.
  Both panels have an `id`, so opening and closing the chat doesn't remount the page (your Expenses filters stay put).
- **Mobile** (under 768 px): the chat slides in as a `Sheet` from the right.
- The page and the chat scroll independently.

**react-resizable-panels v4** (installed by shadcn) changed how sizes are written: **strings are percentages,
numbers are pixels**. So it's `defaultSize="32%"`; `defaultSize={32}` would mean 32 *pixels*. It also uses
`orientation` instead of the older `direction`.

**A shadcn bug fixed:** the generated `components/ui/resizable.tsx` imported `cn` from `"cn"`, which doesn't exist,
instead of `"@/lib/utils"`, so the build would have failed. Corrected by hand: that's the "you own the code" side of
shadcn/ui.

## Run it

`.\run.ps1` from the project folder, and `cd web; npm run dev` (run `npm install` first if you pulled these changes:
`react-resizable-panels` and the scroll-area package were added). Open http://localhost:5173. The chat needs your
Gemini key in `.env` (Phase 2) and the backend on port 8000 (Phase 10's `MCP_URL`).

## Verify it by hand

1. Click **Assistant** in the top bar: the panel opens on the right with three suggestions. Drag the handle to resize it.
2. Click **"How much did I spend on food this month?"** You should see "Thinking…", then a reply in plain text with a
   **get summary** (and/or **list expenses**) badge underneath. Nothing on the page reloads (read-only).
3. Open **Expenses**, keep the panel open, and send **"Add 250 for lunch at Subway today, paid by UPI"**. The reply
   has an **add expense** badge, and the table refreshes by itself with the new row.
4. On the **Dashboard**, ask it to change that expense (e.g. "Actually it was 300"). The cards and charts update
   without a reload. This also shows memory: "it" is understood because the `thread_id` was sent.
5. Ask **"Delete the Subway expense"**. It should ask you to confirm first (a **delete expense** badge, but nothing
   changes on the page). Reply "yes" and the row disappears.
6. Close the panel, go to another page, reopen it: the conversation is still there. **New conversation** (pen icon)
   clears it and starts a new thread.
7. Make the window narrow (under 768 px) and open the Assistant: it slides in as a sheet.
8. Stop the backend and send a message: the reply bubble turns red with "Can't reach the SpendWise API…".

Shift+Enter makes a new line; Enter sends.

## Design questions

**1. The chat panel and the Expenses page are siblings in the layout. How does adding an expense in the chat make the
Expenses table refresh?**

<details><summary>Answer</summary>

Both read a shared context (`DataSyncProvider`) that sits above them. When a reply includes a successful
`add_expense`, the chat hook calls `notifyDataChanged()`, which increments `dataVersion`. The Expenses page lists
`dataVersion` in its loading `useEffect` dependencies, so React re-renders it, the effect sees a new value, and it
fetches the list again from the API. No page reload, and the panel never needs to know which page is open.
</details>

**2. Why does the conversation live in `useChat()` inside `AppLayout`, instead of in `useState` inside `ChatPanel`?**

<details><summary>Answer</summary>

Because `ChatPanel` is unmounted when you close it (and swapped between the resizable panel and the Sheet when the
screen size changes), and React throws away a component's state when it unmounts. `AppLayout` stays mounted across
pages and panel toggles, so state kept there, including the `thread_id`, survives. The panel just receives it as a
prop.
</details>

**3. "Delete the Subway expense" produced a `delete_expense` tool call, but the page didn't refresh. Is that a bug?**

<details><summary>Answer</summary>

No. The first `delete_expense` call is made with `confirmed: false`, which only looks the expense up so the assistant
can ask "are you sure?". Nothing changed in the database, so `changedData()` returns false and no refresh happens.
After you confirm, the call has `confirmed: true`, data really changes, and the page refreshes.
</details>
