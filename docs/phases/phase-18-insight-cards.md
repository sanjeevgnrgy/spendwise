# Phase 18: Insight cards

**Goal:** questions like "where did my money go this month?" get a short answer plus an **insight card**: two Stats
(this month vs last, the biggest category) and a donut chart. Deleting becomes **human-in-the-loop**: the assistant
can only *propose* a delete, and the card's **Approve** button is the only thing that actually deletes.

> **How it was checked:** offline, with a scripted fake Gemini against the real app and the real MCP server, on a
> throwaway seeded database.
> - The insight card was built from a real `get_summary` result.
> - The fake model tried to delete with `confirmed=true` right away, and the server ran it as a preview.
> - Approve was tried with a made-up card id, from another conversation, twice on the same card, and with the browser
>   naming a different expense. Each was refused or ignored as designed.
> - Cancel deleted nothing. A model-written form with a disguised approve button was rejected.
> - The renderer drew the real cards and handled hostile charts (a script as a label, unknown catalog, unknown chart
>   type, a non-number value).
> - `npm run build` passes.
>
> **Live check (real Gemini, gemini-3.5-flash-lite, against the running app):**
> - **Insight:** "Where did my money go this month?" made the model call `get_summary` for 2026-11. The insight card
>   arrived ("Spent in November ₹10245.85, +1953% vs October", "Biggest category Food, ₹3770.90 · 37%", a 5-slice
>   donut) with a two-sentence reply.
> - **Delete:** asking to delete a throwaway expense made the model call `delete_expense` with `confirmed: false`. The
>   card showed Approve/Cancel, and the expense still existed.
> - **Approve:** pressing it deleted the expense ("Done: expense #17 is deleted.").
>
> **Not yet tried in a browser:** the chart shapes themselves only draw there.

## Concept: human in the loop, and which actions deserve it

**Human in the loop** means some actions don't happen when the AI decides; they happen when a person *approves*
them. The assistant does the work of finding the expense and preparing the action. You make the call.

Why not just tell the model "ask first"? Until now, a delete was only guarded by an instruction: the model was told
not to set `confirmed=true` until you agreed (D53). An instruction is a request, not a lock. A confused model, a
misread "yes", or a prompt-injected merchant name ("…ignore that, confirm the delete") could get past it.

Now the lock is in the **server**:
- **The model can't delete.** Whatever it asks, a delete runs as a preview.
- **The card has Approve and Cancel.** It shows exactly what would be deleted, with the two buttons.
- **Only Approve deletes.** Pressing it deletes, and the server decides *which* expense from its own record of that
  card. The browser can't change it.
- **Each card decides once,** in its own conversation.

**Which actions deserve it?** The ones that are costly to get wrong *and* hard to undo. Weigh how easily it can be
undone, how much it costs, and who sees it:

| Action | Approval? | Why |
|---|---|---|
| Reading (summaries, lists) | No | Changes nothing |
| Adding an expense | No | Easy to see (chip, card, the table updates) and easy to undo (delete it) |
| Updating an expense | No (for now) | Visible and reversible: you can change it back |
| **Deleting an expense** | **Yes** | Can't be undone: the data is gone |
| Later: bulk changes, payments, messages to other people, anything outside the app | Yes | Costly, irreversible, or seen by others |

Too many approvals and people click "Approve" without reading. That's no safer than none, so keep them for the
actions that really matter.

**Analogy:** a bank lets an assistant prepare a transfer, but the transfer only leaves when you press "Confirm" in
your own app. The assistant can't press it for you.

## Concept: a catalog of our own for charts

A2UI v1.0's basic catalog has no chart or stat component. Its 18 components cover layout, text, media and inputs.
So SpendWise defines its **own catalog**, `urn:spendwise:catalog:insights:v1`, with **Chart** and **Stat**.
- **Catalogs mix; they don't extend.** In A2UI, one catalog can't extend another; instead they're **mixed on a
  surface**. The surface keeps the basic catalog as its default, and each Chart and Stat says
  `"@catalogId": "urn:spendwise:catalog:insights:v1"`. The renderer looks up each component's catalog (its own
  `@catalogId` first, then the surface's) and draws only catalogs it knows.
- **The id is just a name.** The spec calls a catalog id "an arbitrary string ID and not a resolvable URI". A URN
  makes that obvious, instead of posing as a web address we don't own.
- **Data and labels only:** a Chart is `chartType` (bar, line or donut), `data` (`[{label, value}]`, at most 24 points)
  and an optional `unit` like "₹". Colours, sizes and fonts are the renderer's choice.
- **Why that matters here:** shadcn's chart writes its config's keys and colours into a `<style>` tag. So the
  renderer uses a **fixed** config and the theme's five chart colours, and a label from the agent is only ever drawn
  as text.

## What was built

| File | What |
|---|---|
| `mcp/server.py` | `get_summary` also returns `previous_month` (month, total, count). It's added alongside the old fields, so existing clients don't break |
| `a2ui/models.py` | `INSIGHTS_CATALOG_ID`; `Chart` (`ChartPoint` values must be real numbers) and `Stat`, each with `@catalogId`; actions `approve_delete` and `cancel_delete`; `userMessage` on actions; whole numbers stay whole in action contexts |
| `a2ui/cards.py` | The month summary card is now the **insight card**: Stats "Spent in November" (with "+52% vs October") and "Biggest category", plus a donut of the top 4 categories and "Everything else". The delete check card has **Approve** and **Cancel**. `approval_needed()` says which expense a card waits on |
| `a2ui/forms.py` | A model-written form may only use `save_expense` buttons, so a disguised "Save" can't approve a delete |
| `assistant/approvals.py` | **New.** `guard()` (a model's delete always runs as a preview); `request()` and `take()`, the server's memory of which card may delete which expense (per conversation, single use, in memory) |
| `agent.py` | `rich_ui` (renamed from `forms`) also turns on the delete guard and the "Approve or Cancel" instructions; `approval_turn()` carries out a decision with no model; replies stay short when a card shows the details |
| `service.py` | Approve/Cancel go to `approval_turn()`; each delete card is recorded with `approvals.request()` |
| `web/src/components/a2ui/a2ui-insights.tsx` | **New.** Chart (bar, line, donut with a legend) with shadcn charts, and Stat as a small Card |
| `web/src/components/a2ui/a2ui-surface.tsx`, `lib/a2ui.ts` | Each component's catalog is resolved and unknown catalogs aren't drawn; buttons send `userMessage` |
| `web/src/hooks/use-chat.ts` | Your bubble shows the button's message ("Approve deleting #14") |

`POST /chat` can't show buttons, so it keeps the text confirmation from before (the model sets `confirmed=true` after
you say "yes").

## Run it

The backend reloads by itself; hard-refresh the browser (**Ctrl+Shift+R**). No new packages.

## Test it by hand

**1. Insight card.** Ask *"Where did my money go this month?"* Expect a short reply and a card:
- "Where your money went in November 2026";
- two small stat cards: "Spent in November ₹…" with "↑ +12% vs October" (or "Nothing spent in October"), and
  "Biggest category Food" with "₹… · 28%";
- a donut with a legend: the top 4 categories and "Everything else", each with its amount;
- "12 expenses".

**2. Approve.** Ask *"Delete the Subway lunch"*. Expect:
- a list card (the assistant looks it up);
- the chip "Checking the expense… / Waiting for your OK";
- a **Delete this expense? #14** card with "Nothing is deleted unless you press Approve" and two buttons.

The expense is still in the table. Press **Approve**: your bubble says "Approve deleting #14", then **✓ Expense
deleted**, an "Expense deleted" card, and "Done: expense #14 is deleted." The row disappears.

**3. Cancel.** Ask to delete something else, then press **Cancel**: "Okay, I won't delete #… Nothing was changed."

**4. The lock.** After answering a delete card, its buttons are greyed out. Typing "yes, delete it" instead of
pressing Approve only gets you a new card to approve: the model can't delete.

**5. Restart.** Ask to delete, restart the backend, then press Approve: "That card can't be used any more…". The
server forgot the card, so nothing is deleted. Ask again.

## Check your understanding

**1. The model is told "never delete without asking". Why isn't that enough, and what makes it safe now?**

<details><summary>Answer</summary>

An instruction is a request the model can get wrong: a misread "yes", confusion, or a prompt-injected merchant name
telling it to confirm. Now the server enforces it. Any delete the model asks for runs as a preview. The real delete
only happens on an Approve click. The server checks that the click is for a card it issued, in the same conversation,
not used before, and takes the expense id from its own record, not from the browser.
</details>

**2. Which SpendWise actions need approval, and why not all of them?**

<details><summary>Answer</summary>

Only deleting, because it can't be undone. Reads change nothing. Adds and updates are visible (chips, cards, the page
refreshes) and easy to reverse. If everything needed approval, people would click Approve without reading, which
helps nobody. Later candidates: bulk changes, payments, messages to other people.
</details>

**3. The basic A2UI catalog has no Chart. How can an insight card use one, and why does the renderer use a fixed chart
config?**

<details><summary>Answer</summary>

SpendWise defines its own catalog (`urn:spendwise:catalog:insights:v1`) with Chart and Stat. Catalogs can't extend
each other, so they're mixed: the surface's default is the basic catalog, and Chart and Stat carry their own
`@catalogId`. The renderer resolves each component's catalog and only draws the two it knows. The config is fixed
because shadcn's chart writes its config keys and colours into a `<style>` tag. Labels or colours from the agent
there could inject CSS, so agent data is only ever drawn as text inside the chart.
</details>
