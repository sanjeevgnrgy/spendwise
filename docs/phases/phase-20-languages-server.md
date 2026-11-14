# Phase 20: Languages (the server)

> **Later changes (D180, after Phase 20):** people only read texts written for them. An outside service's own words
> (Gemini's errors), Pydantic's explanation, the tools server's URL and a tool's output no longer reach the client:
> they go to the server log, and a person gets a catalogued text ("A service the app depends on didn't answer
> properly…"). A 422's `detail` is a catalogued text too (`errors` still lists each field), `RUN_ERROR.code` is the
> problem kind, `TOOL_CALL_RESULT.content` is empty, and in the browser a crash shows "Something went wrong" (its
> details go to the console). See [decisions.md](../decisions.md) D180.

**Goal:** finish what Phase 19 started. The web app spoke Hindi, but much of what a Hindi user read still came from
the server in English: the assistant's cards, its progress chips and fixed replies, error messages, payment labels.
Now the server writes every text meant for a person in the request's language, and the assistant's model replies in
it. Decision: D179.

> **How it was checked:** offline with a scripted fake model and an in-memory database, then live.
> - **English unchanged:** the same 38 recorded scenarios as before (REST, every problem type, `/parse`, `/chat`,
>   `/agent` with cards and the approval card) give identical responses, events, cards, chips, MCP tool listing and
>   OpenAPI document. The model calls differ only by the new reply-language line.
> - **Hindi:** 17 scenarios with `Accept-Language: hi`: every error detail, the cards (summary, delete, saved), the
>   built-in form, the chip labels and the fixed replies come back in Hindi; the model is told "Reply in Hindi".
> - **Live** (real Gemini, a copy of the database, the web app in Hindi, 3 chat turns): the replies, chips and cards
>   were Hindi, and the model still sent `Food` and `upi` to the tools.
> - The architecture scans are clean; the web contract was regenerated; `tsc`, `oxlint` and the build pass.
>
> **The Hindi texts were written by an AI** and need a native speaker's review.

## Design: who asks for the language

The browser already knows the language (Phase 19), so it says so on every request, the standard way:

```
GET /api/v1/expenses/999
Accept-Language: hi
→ 404 {"detail": "खर्च 999 नहीं मिला", ...}
```

- **`Accept-Language`, not a parameter:** it's what HTTP has for this (RFC 9110), every client can send it, and it
  stays out of each route's signature and the OpenAPI document. The server picks the best language it speaks (weights,
  then an exact tag before its base language) and falls back to English.
- **It costs nothing in CORS:** `Accept-Language` is a safelisted header, so no preflight.

## Design: where a text is written

- **At the edge, from a key.** A handler deep in a module doesn't know who will read its error, so it doesn't write
  the words: it raises `NotFoundError(translatable(ExpenseText.NOT_FOUND, expense_id=14))`, a key and its values.
  `web/problems.py`, which builds the response, writes it in the request's language. An MCP client, which has no
  language, gets English (`str(error)`).
- **Where the language is known, directly.** The assistant's routes take the language and pass it down, so cards,
  chips, replies and forms are written as they're built: `text(language, ChatText.EXPENSE_SAVED)`.
- **Not everything is for people.** What the model reads (prompts, tool descriptions, tool results) stays English: it
  reads English best, and it's told to answer in the user's language anyway. Logs, codes and data stay as they are.

## Design: catalogs checked as the app starts

Each module keeps its texts beside its code, in `i18n/`, with the same conventions as the web app's:

```python
class ExpenseText(StrEnum):                      # en.py: the keys, and the English source
    NOT_FOUND = "errors.notFound"
EN = {ExpenseText.NOT_FOUND: "Expense {expense_id} not found"}
HI = {ExpenseText.NOT_FOUND: "खर्च {expense_id} नहीं मिला"}   # hi.py
define_catalog(ExpenseText, {Language.EN: EN, Language.HI: HI})   # __init__.py
```

`define_catalog` refuses to start the app if a language lacks a key, has an extra one, or uses a placeholder English
doesn't fill. There's no type checker in this project, so the check runs where it can't be skipped: at import.

## Design: money and dates from CLDR, on both sides

The server used `strftime` ("05 Sep 2026", English only) and hand-written digit grouping. Now it uses Babel, which
reads the same CLDR data as the browser's Intl, so a card and a page write a value identically: "5 Sept 2026",
"13 नव॰ 2026", "₹1,25,000.50". Money is its currency's CLDR format on both sides ("$1,250.50" for USD).

## What was built

| Where | What |
|---|---|
| `core/i18n/` | `Language`, `parse_accept_language`, `define_catalog`, `text`, `Plural`, `Translatable`, `format_day`, `format_month` |
| `core/errors.py`, `web/problems.py` | errors carry a `Translatable`; the detail is written in the request's language (a bug's too) |
| `web/dependencies.py` | `LanguageDep` |
| `modules/*/i18n/` | the catalogs: expenses (errors, payment labels), categories, conversations, assistant (74 keys), web |
| the assistant | the language passed from `/chat` and `/agent` to the cards, form, chips, replies and errors; one prompt line; a model-written form's payment options relabelled by the server |
| the web app | `Accept-Language` on every call and on the stream; payment labels by language; `formatMoney` with Intl's currency format; its language table typed against the server's |
| `requirements.txt` | `babel==2.18.0` |

## Run it

```powershell
.\run.ps1                          # backend (installs Babel on first run after the change)
cd web; npm run dev                # web app, http://localhost:5173
```

## Verify it by hand

1. Switch the app to **हिन्दी** and open the Assistant.
2. Ask "इस महीने मैंने खाने पर कितना खर्च किया?": the progress chip, the card and the reply are in Hindi.
3. Ask to delete an expense: the approval card is in Hindi; **स्वीकार करें** deletes it, and the reply is Hindi.
4. On the Expenses page, open **खर्च जोड़ें** and save an amount of 0: the error says "राशि 0 से ज़्यादा होनी चाहिए".
5. Switch back to English: the same steps show English.

## Design questions

**1. Why does the error carry a key, rather than the handler being told the language?**

<details><summary>Answer</summary>

Because the handler can't know who will read the error. The same `GetExpense` serves the web app (a person, in
Hindi), MCP clients (no language at all) and the assistant's tools (the model). A key and its values can be written
by whoever answers, in whatever language that reader wants; a string written early would be wrong for someone.
</details>

**2. Why are the prompts and tool descriptions left in English?**

<details><summary>Answer</summary>

They're instructions for the model, not texts for the user. Models follow English instructions most reliably, and
one line ("reply in Hindi") is enough for the reply. Translating the prompt would mean testing the model's behaviour
again in every language, for no gain the user would see.
</details>

**3. What stops someone adding an English error and forgetting the Hindi?**

<details><summary>Answer</summary>

The catalog's check at startup: a key in `en.py` without its `hi.py` twin stops the app with the key's name. In the
web app, the compiler does the same job.
</details>
