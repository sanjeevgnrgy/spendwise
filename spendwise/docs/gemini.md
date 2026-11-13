# Gemini

How SpendWise talks to Gemini, which models a free account can use, and what to watch out for.

> Facts about Google's models, pricing and limits were checked against Google's docs on 2026-11-13
> (`aistudio.google.com/docs/...`; the old `ai.google.dev/gemini-api/docs/...` links redirect there).
> They change often, so re-check before relying on them.

## Setup

1. Create a key at https://aistudio.google.com/apikey.
2. Put it in `spendwise/.env` after `GEMINI_API_KEY=` (no quotes, no spaces).
3. Set `GEMINI_MODEL` (currently `gemini-3.8-flash`).
4. Restart the server. `.env` is read once at startup, and auto-reload only watches `.py` files.

Never paste the key into chat, code, or any committed file.

## How the settings are read

- `backend/app/core/config.py` reads `.env` into `settings` (pydantic-settings).
- A real environment variable with the same name **overrides** `.env`.
- The key is a `SecretStr`, so it prints as `**********` if settings are ever logged.
- The key is passed explicitly to `genai.Client(api_key=...)`. Without that, the SDK would silently prefer
  a `GOOGLE_API_KEY` environment variable over `GEMINI_API_KEY` if both existed.

## Models and the free tier

| Model | Free tier | Notes |
|---|---|---|
| `gemini-3.8-flash` | ✅ | **SpendWise uses this.** Labelled stable. |
| `gemini-3.6-flash`, `gemini-3.5-flash-lite` | ✅ | Labelled stable |
| `gemini-4-hydrogen` | ✅ | Model used in Google's quickstart |
| `gemini-4-argon`, `gemini-4-carbon` | ❌ | "not available on the Free tier" |
| `gemini-2.5-flash`, `gemini-2.5-pro` | — | Deprecated; rerouted to newer models from 2026-12-01 |

To switch models, change `GEMINI_MODEL` in `.env` and restart. No code changes needed.

**Limits:** the docs don't list free-tier requests per minute or per day for each model. Your real limits
are in AI Studio at https://aistudio.google.com/rate-limit.
- Limits apply **per Google project**, not per key.
- Daily quotas reset at midnight Pacific time: 1:30 PM IST in US winter, 12:30 PM IST in US summer.
- Some projects need verification before the free tier works. Moving to paid requires setting up billing in AI Studio.

## Privacy

- **Free tier:** Google's pricing page says free-tier content is **used to improve Google's products**.
  The paid tier says it is not. Use sample data, not your real finances, while on the free tier.
- **`store=False`:** SpendWise sets this on every call, so Google doesn't keep the conversation for later
  retrieval. (By default it would: 1 day on free, 55 days on paid.) This is separate from the data-use
  terms above and does **not** change them.

## How the app calls Gemini

All Gemini code is in `backend/app/core/llm.py`:

```python
interaction = client.interactions.create(model=settings.gemini_model, input=prompt, store=False)
return interaction.output_text
```

It uses the **Interactions API** (`client.interactions.create`), which Google recommends for new projects.
The older `client.models.generate_content` still works and is fully supported, but Google calls it legacy.
See [decisions.md](decisions.md) D6–D9 for the reasoning.

## When something goes wrong

| What you see from `POST /ask` | Meaning | Where to look |
|---|---|---|
| `422` | The request body is invalid, e.g. an empty prompt or over 4000 characters | The `detail` field says which rule failed |
| `500 Internal Server Error` | Our setup is wrong: `GEMINI_API_KEY` or `GEMINI_MODEL` isn't set | The server terminal says which setting is missing |
| `502` with "API key not valid" | Gemini rejected the key | Re-copy the key into `.env`, then restart |
| `502` with a quota or rate-limit message | Free-tier limit reached | AI Studio rate-limit page; wait for the reset |
| `502` mentioning the model | The model isn't available to your key | Pick a free-tier model from the table above |

**500 vs 502:** a 500 means *our* server has a problem; a 502 means a service we depend on (Gemini) failed.

## Tokens, briefly

- A token is a chunk of text, about **4 characters** for Gemini; 100 tokens is roughly 60–80 English words.
- Input (your prompt), output (the answer) and the model's thinking are all counted.
- `/ask` caps prompts at 4000 characters (about 1000 tokens) to limit cost and abuse.
- Each response reports its usage (`interaction.usage`: `total_input_tokens`, `total_output_tokens`,
  `total_thought_tokens`, `total_tokens`). SpendWise doesn't show these yet.
