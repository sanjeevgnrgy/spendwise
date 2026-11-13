# Phase 6: Structured output

> **Later changes:**
> **Refactor (after Phase 18):** `/parse` is `POST /api/v1/parse`, a query (`ParseExpenseText`) in the assistant
> module; the model call is `core.llm.ask_for_json()`. See [refactor-architecture.md](refactor-architecture.md).

**Goal:** `POST /parse` turns a note like *"Paid 450.50 at Swiggy yesterday via GPay"* into a structured
expense (amount, currency, category, merchant, date, payment method, note), using Gemini's structured
output, **without saving it**.

> **Later changes:** the tests mentioned below were removed after Phase 8 ([decisions.md](../decisions.md) D64).
> This page records Phase 6 as it was built.

## Concepts

**Structured output.** Normally a model answers in free text, which your code then has to pick apart and
hope it's in the expected format. With structured output, you send a **JSON schema** with the request:
the field names, their types, which values are allowed, which may be `null`. Gemini then *can only*
produce JSON that fits that schema. This is called **constrained decoding**: at each step, any token that
would break the schema simply isn't allowed. You get exact field names and types, ready for
`ParsedExpense.model_validate_json(...)`.

**Analogy:** the difference between "write me a letter about your expense" and handing someone a printed
form with labelled boxes, where a box that only takes a date won't accept anything else.

**Shape, not truth.** The schema guarantees the answer has the right *shape*. It does not guarantee the values
are *true*. That's why it matters what the schema allows:

**What happens when the text has no amount?** It depends on whether the schema lets Gemini say "I don't know":

- If `amount` were a **required number**, Gemini would be *forced* to produce a number for
  "Dinner at Swiggy last night", so it would invent one (0, or a plausible price). That's silently wrong data.
- In SpendWise, `amount` is **required but nullable** (`"type": ["string", "null"]`), and its description says
  "null if the text does not state an amount. Never guess." So Gemini answers `"amount": null`.
- The service then reports `"missing_fields": ["amount", ...]`. Those are fields `POST /expenses` would need,
  so the UI or assistant knows exactly what to ask the user next.

Google's own advice: *"Mark properties as required where possible and allow null values when a field can be
empty."*

## What was built

| File | What |
|---|---|
| `modules/assistant/schemas.py` | `ParseRequest`, `ParsedExpense` (the schema Gemini fills), `ParseResponse` (`expense` + `missing_fields`) |
| `modules/assistant/parse.py` | **New.** `parse_expense(text, today, category_names)`, `missing_fields(parsed)` |
| `modules/assistant/service.py` | `parse_expense_text(session, text)`: gets the category names and today's date, calls `parse` |
| `modules/assistant/router.py` | `POST /parse`; no try/except any more (see below) |
| `core/llm.py` | `ask_gemini_for_json(prompt, schema, system_instruction)`; timeouts and retries limited |
| `core/errors.py` | `ExternalServiceError` → **502**, handled in one place (Gemini errors are a kind of it) |
| `tests/assistant/test_parse.py` | **New.** 9 tests with a fake Gemini (offline, free, repeatable) |

**The schema is the Pydantic model** (`schemas.py`). Its field descriptions are instructions Gemini reads:

```python
class ParsedExpense(BaseModel):
    """One expense read from a short note the user wrote. Use null for anything the note does not say."""

    # Gemini's schema has no decimal type. A string keeps the exact digits; Pydantic turns it into a Decimal.
    amount: Annotated[Decimal | None, WithJsonSchema({"type": ["string", "null"]})] = Field(
        description='The amount as a plain number string, e.g. "1250.50", with no currency symbol or commas. '
        "null if the text does not state an amount. Never guess an amount."
    )
    currency: str = Field(description="ISO 4217 code such as INR, USD or EUR. INR unless another currency is clearly stated.")
    category: str | None = Field(description="The best matching category from the allowed list, or null if none fits.")
    merchant: str | None = Field(...)
    spent_on: date = Field(description="... Work out words like 'yesterday' ... from today's date; use today if no date is mentioned.")
    payment_method: expenses.PaymentMethod | None = Field(...)
    note: str | None = Field(...)
```

**Sending it** (`core/llm.py`). This is the Interactions API's structured output, as in Google's docs:

```python
response_format={"type": "text", "mime_type": "application/json", "schema": schema}
```

**Only real categories** (`parse.py`). The names come from the categories module's public interface and are put
into the schema as an `enum` **on each request**, because they live in the database and can change:

```python
schema["properties"]["category"] = {
    "anyOf": [{"type": "string", "enum": category_names}, {"type": "null"}], ...
}
```

**Model output is data, not truth.** After Gemini answers, `parse.py`:
- validates the JSON with Pydantic (a wrong shape becomes a 502), and
- double-checks the category is in the list (if not, it becomes `null` and shows up in `missing_fields`).

**"Yesterday" works** because the system instruction says `Today is Friday, 2026-11-13.` The same instruction
tells Gemini that the note is data to extract from, and that any instructions written inside it must be ignored.

**Nothing is saved.** `/parse` only suggests an expense. Saving stays a separate, deliberate step through
`POST /expenses`, so a misread note never lands in your data by itself.

## Two things found while testing it live

1. **`gemini-3.8-flash` was overloaded.** Google answered `503: "gemini-3.8-flash is currently experiencing
   high demand ... Please try again later."` This is temporary, and on Google's side.
2. **That made our API hang for minutes,** because the SDK's defaults retry up to 5 times with waits of up to
   60 s. `core/llm.py` now gives up on an attempt after 30 s and tries at most twice, so an outage becomes a
   clear **502 within about a minute** (measured: 32 s).

The live checks then ran on `gemini-4-hydrogen` (also free tier), and all three worked:

| Note | Gemini's structured answer | `missing_fields` |
|---|---|---|
| "Paid 450.50 at Swiggy yesterday via GPay" | 450.50 · INR · Food · Swiggy · 2026-11-12 · upi | `[]` |
| "Dinner at Swiggy last night" | **null** · INR · Food · Swiggy · 2026-11-12 · null · "Dinner" | `["amount", "payment_method"]` |
| "Uber to the airport, Rs 1,250 last Friday, paid by card" | 1250 · INR · Transport · Uber · 2026-11-06 · card | `[]` |

## Run it

From the project folder: `.\run.ps1`. No new packages. Make sure `.env` has your key, and that the database has
categories (`backend\seed.py`).

If `/parse` returns **502** with "experiencing high demand", Gemini is overloaded. Wait a few minutes, or
temporarily set `GEMINI_MODEL=gemini-4-hydrogen` in `.env` and restart.

## Test it by hand

In `/docs`, open **POST /parse**, click **Try it out**, and send:

```json
{"text": "Paid 450.50 at Swiggy yesterday via GPay"}
```

You should get **200**: `"amount": "450.50"`, `"category": "Food"`, `"merchant": "Swiggy"`, `spent_on` = yesterday,
`"payment_method": "upi"`, and `"missing_fields": []`. Then try:

- `"Dinner at Swiggy last night"` → `"amount": null`, `"missing_fields": ["amount", "payment_method"]`.
- `"Coffee $4.50 this morning"` → `"currency": "USD"`. The category is probably Food, and the merchant is probably null (missing).
- Afterwards, **`GET /expenses`** shows nothing new: `/parse` never saves.

Exact wording (like `note`) can vary between runs; the structure never does.

Automated: `python -m pytest` → **47 passed** (9 new in `tests/assistant/`, with Gemini replaced by a fake via
`monkeypatch`, so they need no key or network).

## Check your understanding

**1. Suppose `amount` were a plain required `Decimal` (not nullable) in the schema, and the user typed
"Dinner at Swiggy". What would Gemini have to do, and why is that dangerous?**

<details><summary>Answer</summary>

Constrained decoding only allows output that fits the schema, and a required number can't be left empty. So
Gemini would have to produce *some* number: 0, or a made-up "typical" price. It would look exactly like a real
amount, so nothing downstream could tell it was invented. That's silently wrong data. With a nullable field,
Gemini can say `null`, and we turn that into `missing_fields: ["amount"]` so the user gets asked instead.
</details>

**2. Why are the category names put into the schema as an `enum` on every request, instead of only being
listed in the prompt, or written into the code once?**

<details><summary>Answer</summary>

Categories live in the database and can change, so a list written into the code would go stale. Listing them
only in the prompt is a *suggestion*; Gemini could still answer "Snacks". Putting them in the schema's `enum`
*constrains* the output, so only real names (or null) can be produced. We still check afterwards, because model
output is data to verify, not trust.
</details>

**3. Why does `POST /parse` return `missing_fields` and save nothing?**

<details><summary>Answer</summary>

A model can misread a note: the wrong date, or the wrong category. Saving automatically would put those
mistakes straight into your data. Returning a suggestion lets a person (or later the assistant, after asking)
confirm or fix it, then save it deliberately with `POST /expenses`. `missing_fields` says exactly what `POST /expenses`
still needs, so the next step is clear: ask "How much was it?" instead of failing.
</details>
