# Phase 16: A2UI card

**Goal:** after the assistant saves an expense, the chat panel shows a small "Expense saved" card (amount, merchant,
category, date). The card isn't HTML from the server. It's an **A2UI** description, which the browser draws with its
own shadcn/ui components.

The phase asked for the `add_expense` card. On request, every tool now has one: expense updated, delete preview /
expense deleted, the month's summary, and a list of found expenses.

> **How it was checked:** offline, with no Gemini calls.
> - The Pydantic models accepted a valid card and rejected seven broken ones.
> - The real `/agent` stream (fake Gemini, real MCP server) carried the card as a `CUSTOM` event right after
>   `add_expense`'s result, and only then.
> - The web renderer drew the real card, plus hostile descriptions, to HTML with React's server renderer.
> - All seven cards were built from **real** MCP tool results on a throwaway database (add, update, delete preview,
>   confirmed delete, summary, list, empty list), then rendered, with no placeholders.
> - `npm run build` passes.
>
> **Not yet seen in a browser or with real Gemini.**

## Concept: why the agent sends data describing UI, not HTML

HTML is code. If an agent could send HTML, then anything that can influence the agent could put things on your screen:

- scripts;
- tracking images;
- a fake "Confirm payment" form;
- styles that cover the real page.

That includes a prompt-injected merchant name or a malicious tool result. You'd have to trust every byte the model
produced.

**A2UI** (Agent-to-User Interface, an open protocol from Google) sends a **description** instead: "a Card containing a
Column of these three Texts". The browser builds it from components on **its own allowlist**, drawn with **its own**
code:

- **Safe:** unknown types become a harmless placeholder. Text is always shown as text, never parsed as markup. The
  worst a bad description can do is look odd.
- **Consistent:** cards use the app's theme, fonts and dark mode, because they *are* the app's components.
- **Portable:** the same JSON could be drawn by a mobile app with native widgets.
- **Easy to check:** it's plain data, so it can be validated against a schema on both sides.

**Analogy:** ordering from a menu instead of letting a stranger cook in your kitchen. The agent can only pick dishes
on the menu (the catalog), and your own kitchen (the renderer) makes them.

## Concept: what an A2UI message looks like (v1.0)

A UI is a **surface** made of a **flat list** of components that point at each other by `id`. Drawing starts at
`"root"`. This is the actual card SpendWise sends:

```json
{"version": "1.0",
 "createSurface": {
   "surfaceId": "expense_saved_a720bba2038c",
   "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json",
   "components": [
     {"id": "root",     "component": "Card",   "child": "body"},
     {"id": "body",     "component": "Column", "children": ["title", "amount", "merchant", "divider", "details"]},
     {"id": "title",    "component": "Text",   "text": "Expense saved", "variant": "caption"},
     {"id": "amount",   "component": "Text",   "text": "₹250.00", "variant": "body"},
     {"id": "merchant", "component": "Text",   "text": "Subway", "variant": "body"},
     {"id": "divider",  "component": "Divider"},
     {"id": "details",  "component": "Row",    "children": ["category", "date"], "justify": "spaceBetween"},
     {"id": "category", "component": "Text",   "text": "Food", "variant": "caption"},
     {"id": "date",     "component": "Text",   "text": "13 Nov 2026", "variant": "caption"}
   ]}}
```

- **Why flat with ids, not nested?** A model (or code) can send or replace any one component by its id, and a
  renderer can draw parts as they arrive. The spec has `updateComponents` for that, which we don't use yet.
- **Getting it to the browser:** AG-UI has no A2UI event, so the message rides in AG-UI's extension event:
  `{"type": "CUSTOM", "name": "a2ui", "value": <the message above>}`.
- **The catalog SpendWise allows** is Text, Card, Row, Column, List, Button and Divider, a subset of A2UI's basic
  catalog.

## What was built

| File | What |
|---|---|
| `modules/assistant/a2ui/models.py` | **New.** Pydantic models for the seven components and the createSurface, updateComponents and deleteSurface messages. They're strict like the spec: unknown fields, hyphenated ids, components outside the catalog, a missing `root` and dangling child ids are all rejected |
| `modules/assistant/a2ui/cards.py` | **New.** One builder per tool result, and `card_for(tool, result)`, which picks the right one from a table |
| `modules/assistant/a2ui/__init__.py` | **New.** What the rest of the assistant module uses |
| `modules/assistant/agent.py` | `ToolFinished` now carries the tool's `name` |
| `modules/assistant/service.py` | After a successful tool with a card: `CustomEvent(name="a2ui", value=card.to_json())` |
| `web/src/lib/a2ui.ts` | **New.** Types, and `applyA2uiMessage()`, which checks each incoming message and adds, updates or deletes surfaces |
| `web/src/components/a2ui/a2ui-surface.tsx` | **New.** The renderer: each allowed component becomes one of ours; anything else becomes a "Can't show …" placeholder |
| `web/src/hooks/use-chat.ts`, `api.ts`, `components/chat/chat-message.tsx` | `CUSTOM` "a2ui" events become `surfaces` on the reply, drawn between the tool chips and the text |

**The renderer, component by component:**

| A2UI | Drawn as |
|---|---|
| Text | `<span>`, `text-sm` (body) or `text-xs text-muted-foreground` (caption). React escapes the text; nothing uses `innerHTML` |
| Card | shadcn `Card` (small) with its one child in `CardContent` |
| Row / Column | `flex-row` / `flex-col`. `justify` and `align` pick from fixed class tables |
| List | a flex `div` with `role="list"`, vertical or horizontal |
| Divider | shadcn `Separator`, horizontal or vertical |
| Button | shadcn `Button` (primary → filled, default → outline, borderless → ghost), **disabled** until actions are added |
| anything else | a dashed "Can't show …" note |

Built by code, not by the model, for now. The card's values come from the tool's result and are only ever shown as
text.

**The cards, one per tool:**

| Tool result | Card |
|---|---|
| `add_expense` | "Expense saved": amount, merchant, then category and date |
| `update_expense` | "Expense updated": the same layout, with the new values |
| `delete_expense`, not confirmed | "Delete this expense?" plus what would go, and "Nothing is deleted until you reply "yes"." |
| `delete_expense`, confirmed | "Expense deleted": what was removed |
| `get_summary` | "Spending in November 2026": the total, the number of expenses, then a List of categories with totals, biggest first |
| `list_expenses` | "Found 14 expenses": a List of up to 10 (merchant, category · date, amount), then "Showing the newest 10 of 14". An empty result says "No matching expenses" |

Every card gets a new surface id (for example `expense_updated_e97bf19f6ade`). The same expense can be updated twice
in one chat, and the spec doesn't allow creating the same surface twice.

**Expense ids:** the expense cards show the expense's id (`#15`) in the top-right corner, and each list row starts
with it (`#14 · Food · 13 Nov 2026`). The Expenses table has a matching **ID** column. So when the assistant asks
"which one?", you can answer "delete #14"; its instructions say what `#14` means (D120).

## Run it

`.\run.ps1` (it reloads on its own if it's already running) and `cd web; npm run dev`. Then hard-refresh the browser
(Ctrl+Shift+R). Needs your Gemini key in `.env`.

## Test it by hand

**1. The card.** With the Assistant open, send "Add 250 for lunch at Subway today, paid by UPI". You should see:
- the chip **Saving expense…**, then **✓ Expense saved**;
- right under it, a small card: "Expense saved" (small, grey), **₹250.00**, **Subway**, a line, then **Food** on the
  left and the date on the right;
- then the reply text.

It follows light and dark mode like the rest of the app.

**2. The other cards.**
- "Change the Subway lunch to 300" gives an "Expense updated" card.
- "How much did I spend this month?" gives the month's summary card with its category list.
- "Show my food expenses" gives a list card.
- "Delete the Subway expense" gives a list card (the assistant looks it up first) and a "Delete this expense?" card.
  Nothing has been deleted at that point. Reply "yes" to get an "Expense deleted" card.

A failed tool (red chip) never gets a card.

**3. The raw event.** As in Phase 15, send the run with `curl.exe -N` and look for:

```
data: {"type":"CUSTOM","name":"a2ui","value":{"version":"1.0","createSurface":{"surfaceId":"expense_…", …}}}
```

It comes right after the tool's `TOOL_CALL_RESULT` (and, for a tool that changed data, after the `STATE_SNAPSHOT`).

**4. What the renderer refuses** (from the offline check, so you know what to expect):

| Description sent | What you see |
|---|---|
| Text `<script>alert(1)</script>` | that exact text, shown literally; nothing runs |
| `{"component": "Iframe", …}` | "Can't show a "Iframe" component" |
| A Column whose child is itself | 12 levels deep, then "Can't show components nested this deep" |
| `justify: 'x" onmouseover="…'` | no extra class or attribute at all |
| A Text bound to `{"@path": …}` | "Can't show a data-bound text" (bindings come later) |
| `"version": "0.8"` | ignored |

## Check your understanding

**1. Why does the agent send `{"component": "Text", "text": "…"}` instead of `<p>…</p>`?**

<details><summary>Answer</summary>

HTML is code: it can carry scripts, tracking, fake forms or styles, and anything that influences the model could put
them on your screen. An A2UI description can only name components from the browser's allowlist. The browser draws
them with its own trusted components and shows text as text. So a bad description can at worst look odd, never run
anything. It also keeps cards on-theme and could be drawn by other clients, such as a mobile app.
</details>

**2. The card is a flat list of components with ids. How does the renderer know where to start, and what stops a
component that lists itself as its own child from freezing the page?**

<details><summary>Answer</summary>

Drawing starts at the component whose id is `"root"`, as the spec says, and each component draws its children by
looking up their ids. A self-reference would recurse forever, so the renderer counts depth and stops at 12 with a
"Can't show" note. On the server side, `CreateSurface` refuses a card with no root, duplicate ids, or children that
don't exist.
</details>

**3. Where is the card built, and why not let Gemini write it?**

<details><summary>Answer</summary>

In `modules/assistant/a2ui/cards.py`, by code, from `add_expense`'s actual result, and only when the call succeeded.
That way the card always shows what was really saved, in a known-good shape that's validated before it's sent. A
model-written card could get a value wrong or produce something invalid. Letting the model compose UI from the catalog
is a step for later, and the same validation and renderer would then protect it.
</details>
