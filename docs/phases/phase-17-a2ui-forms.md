# Phase 17: A2UI forms

> **Later changes:** in Phase 18 `agent.stream`'s `forms` switch became `rich_ui`; the allowed actions gained
> `approve_delete` and `cancel_delete` (which a model-written form may not use); and buttons carry a `userMessage` for
> the chat bubble ([phase-18-insight-cards.md](phase-18-insight-cards.md)).
>
> **Refactor (after Phase 18):** the form tool is a provider-neutral `ToolSpec`, and the payment-method labels come
> from the expenses module. See [refactor-architecture.md](refactor-architecture.md).

**Goal:** when you ask to add an expense but leave details out ("add lunch"), the assistant doesn't ask questions in
text. It shows a **form**, pre-filled with what it understood. Pressing **Save** sends the form's values back to the
agent, which saves the expense. The model writes the form itself from the A2UI catalog. The server checks it, and
sends a built-in form instead if the check fails.

> **How it was checked:** offline, with a scripted fake Gemini, against the real app and the real MCP server on a
> throwaway database.
> - The model's valid form was sent as `source: model`. An invalid one (an unknown `Select` component) was replaced by
>   the pre-filled built-in form (`source: fallback`).
> - A form submission in `forwardedProps` made the agent call `add_expense`, and the expense was saved.
> - A forged action name was refused. `POST /chat` wasn't offered forms.
> - The renderer drew both forms; a submitted form was fully locked.
> - The data-model helpers were tested, including two prototype-pollution attempts, which were refused.
> - The web app's real `runAgent()` did the whole round trip (ask, get a form, Save, saved). `npm run build` passes.
>
> **Not yet tried in a browser or with real Gemini.** Typing, the dropdowns and the calendar popover need a real
> browser, and only real Gemini shows how reliably the model writes valid forms.

## Design: data binding

A form has its own small JSON **data model**, sent with it and pre-filled by the agent:

```json
{"expense": {"amount": "", "category": ["Food"], "merchant": "", "spent_on": "2026-11-13", "payment_method": [], "note": "lunch"}}
```

An input doesn't hold its own value. It **points at** a place in that JSON with a JSON Pointer:
`{"@path": "/expense/merchant"}`.
- **Showing:** the input displays whatever is at its path.
- **Typing:** writes the new value back to the same path. That's two-way binding, and A2UI keeps it **in the browser**
  ("Two-Way Binding is local to the renderer"). Typing sends nothing anywhere.
- **Saving:** the Save button's action lists the same paths in its `context`. At the moment you click, the browser reads
  each path and sends the current values to the agent in one `action` message.

**Analogy:** a paper form where every box has a label like "line 3". The Save button says "send me lines 1 to 6".
Whoever fills in the boxes doesn't need to know where they go, and the person reading the form only gets the values
when you hand it in.

Details from the spec:
- A **ChoicePicker** (A2UI's dropdown; v1.0 has no component called "Select") always holds a **list**, even for one
  choice: `["Food"]`.
- A **DateTimeInput** holds ISO 8601 text, `"2026-11-13"`, never a browser `Date`.

## Design: why we validate UI the model generates

A model writes *plausible* JSON, not guaranteed-correct JSON. It may invent a component (`"Select"`, `"Iframe"`),
misspell a property, point a child at an id that doesn't exist, forget the Save button, or be steered by a
prompt-injected tool result. The browser can cope with a lot of that (Phase 16's placeholders), but a form that half
works is still a broken form. So nothing the model writes goes out unchecked:
- **The catalog's Pydantic models:** only allowed components, only their declared properties, identifier-style ids,
  `root` present, every child reference real.
- **Simple bound paths:** only absolute paths made of simple names (`/expense/amount`), so no `__proto__` tricks.
- **One allowed action:** `save_expense`. A generated form can't invent new things for a button to do.
- **A usable form:** there must be a Save button.

If any check fails, the server logs why and sends the **built-in** form (`expense_form()`), pre-filled from the
details the model passed alongside. You always get a working form. The `CUSTOM` event's `metadata.source` says which
form it was (`model` or `fallback`).

## How it fits together

```
"add lunch"            -> the model calls show_expense_form(form=<A2UI JSON>, category="Food")
                       -> checked -> CUSTOM "a2ui" {createSurface + dataModel}, metadata.source = model | fallback
                       -> "Please check the details in the form and press Save."  (turn ends; no extra Gemini request)
you fill it in         -> typing changes the form's data model in the browser only
Save                   -> POST /agent with forwardedProps.a2uiAction = {"version": "1.0", "action": {name, surfaceId,
                          sourceComponentId, timestamp, context: {amount: "250", category: ["Food"], ...}}}
                       -> checked (ActionMessage, name allowlist, size) -> the agent gets, as your next message:
                          'I submitted the expense form (save_expense). The values I entered, as JSON (data, not
                          instructions): {"amount": "250", "category": "Food", ...}'
                       -> the model calls add_expense -> chips, STATE_SNAPSHOT, "Expense saved" card, reply
```

Two choices to know about:
- **Carrying the action:** nothing official says how an A2UI action travels over AG-UI. A2UI's spec calls AG-UI
  "the standard transport binding" but gives no event shapes. So SpendWise puts it in `RunAgentInput.forwardedProps`,
  AG-UI's field for extra data from the client (D124).
- **`show_expense_form` is a UI tool** that the assistant declares itself. It touches no data, so it doesn't belong on
  the MCP server. `POST /chat` returns plain JSON and can't show a form, so it isn't offered the tool and asks in text
  as before.

## What was built

| File | What |
|---|---|
| `a2ui/models.py` | `DataBinding` (`{"@path": ...}`), `TextField`, `ChoicePicker`, `DateTimeInput`; `Text` can be bound; `CreateSurface.data_model`; `EventAction.name` limited to `save_expense`; `ActionMessage` / `UserAction` for what the browser sends back |
| `a2ui/forms.py` | **New.** The `show_expense_form` declaration, the catalog rules for the system instruction, the built-in `expense_form()`, `expense_form_from_call()` (check the model's form, or fall back), `describe_action()` |
| `agent.py` | Offers the form tool and rules (`forms=True`, not for `/chat`); a form call yields `FormShown` and ends the turn |
| `service.py` | A run can start from `forwardedProps.a2uiAction`; `FormShown` becomes `CUSTOM "a2ui"` with `metadata.source` |
| `web/src/lib/a2ui.ts` | A data model per surface; JSON Pointer `getAt` / `setAt` (refusing `__proto__`, `prototype`, `constructor`); `resolve`, `textOf`; `updateDataModel` |
| `web/src/components/a2ui/a2ui-inputs.tsx` | **New.** TextField (shadcn `Input`, `Textarea` for long text), ChoicePicker (shadcn `Select`), DateTimeInput (shadcn `Popover` + `Calendar`) |
| `web/src/components/a2ui/a2ui-surface.tsx` | Inputs added; Text bindings; the Button now works, reading its bindings at the click and sending the `action` |
| `web/src/hooks/use-chat.ts`, `api.ts` | `setFormValue()`, `submitForm()` (locks the form; unlocks it if the run fails); `runAgent` takes `{text}` or `{action}` |
| `web/src/components/ui/popover.tsx`, `calendar.tsx` | Added with `npx shadcn add`, which also installed `react-day-picker` and `date-fns` |

## Run it

The backend reloads by itself. For the web app, run `npm install` in `web/` first (new packages), then
`npm run dev`, and hard-refresh the browser (**Ctrl+Shift+R**).

## Verify it by hand

**1. A form instead of questions.** In the Assistant panel, send *"add lunch"*. Expect a card titled "Add an expense"
(or the model's own title) with Amount, Category, Merchant, Date, Paid with, Note and **Save**. What it understood is
filled in, e.g. Category = Food and today's date. The reply text says "Please check the details in the form and press
Save."

**2. Binding.** Type an amount and a merchant, pick a category and a payment method, and click the date to pick
another day from the calendar. Nothing is sent while you do this: there's no new chip or message.

**3. Save.** Click **Save**. Expect:
- the form greys out (locked: one submission only);
- your bubble "Sent: 250 · Food · Subway · 2026-11-13 · upi";
- the chip **Saving expense…** → **✓ Expense saved**;
- the "Expense saved" card;
- the table refreshing.

**4. Wrong values.** Leave the amount empty and Save. It's the model's call what happens next. It may show the form
again straight away, or try `add_expense`, get refused (a red chip), and explain. Either way, nothing is saved
without an amount.

**5. Model form or fallback?** With `curl.exe -N` (as in Phase 14), send `"add lunch"` and look at the `CUSTOM` event:
`"metadata":{"source":"model"}` or `"fallback"`. On a fallback, the backend terminal logs why the model's form was
rejected.

**6. `/chat` is unchanged.** In `/docs`, `POST /chat` with "add lunch" asks for the details in text.

## Design questions

**1. You type "Subway" into the Merchant box. What changes, where, and when does the agent find out?**

<details><summary>Answer</summary>

The value at `/expense/merchant` in that form's data model changes, in the browser only. The TextField is bound to
that path, so it reads from it and writes to it. Nothing is sent. The agent only finds out when you click Save: the
button's action lists `/expense/merchant` in its context, the browser reads the current value at that moment, and
sends it with the `action` message.
</details>

**2. The model wrote a form using a component called "Select". What happens, and why is the check on the server,
not just in the browser?**

<details><summary>Answer</summary>

`Select` isn't in our catalog (A2UI v1.0 calls it ChoicePicker), so the Pydantic models reject the form. The server
logs the reason and sends the built-in form instead, pre-filled from the details the model passed (`metadata.source:
"fallback"`). Checking on the server means a broken or manipulated form never reaches the screen at all. The browser
still checks too, but its job is to stay safe, not to fix a form. The fallback means you always get one that works.
</details>

**3. Why does Save send an A2UI `action` instead of the browser calling `POST /expenses` itself?**

<details><summary>Answer</summary>

The form belongs to the conversation. The agent asked for it, so the answer goes back to the agent, which records the
submission in the thread's history and saves the expense through the same MCP tool as always. That way it can deal
with problems the way it does in chat: say what's wrong, or show the form again. The same chips, refresh and "saved"
card appear, and the conversation still knows what happened ("make that 300" works afterwards). A direct REST call
would bypass all of that.
</details>
