# Gemini

How SpendWise talks to Gemini, which models a free account can use, and what to watch out for.

> Facts about Google's models, pricing and limits were checked against Google's docs on 2026-11-13
> (`aistudio.google.com/docs/...`; the old `ai.google.dev/gemini-api/docs/...` links redirect there).
> They change often, so re-check before relying on them.

## Setup

1. Create a key at https://aistudio.google.com/apikey.
2. Put it in `.env` in the project folder, after `GEMINI_API_KEY=` (no quotes, no spaces).
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
| `gemini-3.6-flash`, `gemini-3.5-flash-lite` | ✅ | Labelled stable. On 2026-11-13, when both flash models answered 503 "high demand", flash-lite still answered (in about 4 s) |
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

## Structured output

`ask_gemini_for_json(prompt, schema, system_instruction)` makes Gemini answer with JSON that fits a schema
(used by `POST /parse`, see [phases/phase-6-structured-output.md](phases/phase-6-structured-output.md)):

```python
response_format={"type": "text", "mime_type": "application/json", "schema": SomeModel.model_json_schema()}
# then: SomeModel.model_validate_json(interaction.output_text)
```

- **Supported schema features** (Google's docs, 2026-11-13): `type` (including `null`, and type arrays like
  `["string", "null"]`), `properties`, `required`, `enum`, `format` (`date`, `date-time`, `time`), `minimum`/`maximum`,
  `items`, `minItems`/`maxItems`, `title`, `description`. `minLength`/`maxLength` and a few others are **ignored**, so
  validate those yourself (Pydantic does).
- **Make fields required and allow `null`** for anything that might be unknown. Otherwise the model must invent a value.
- **Descriptions are instructions:** Gemini reads each field's `description`.
- Very large or deeply nested schemas can be rejected with `400 INVALID_ARGUMENT`.

## Function calling

`stream_gemini_with_tools(history, tools, system_instruction, thinking_level)` runs one step of a tool-using
conversation, streamed (used by `POST /chat` and `POST /agent`, see
[phases/phase-7-function-calling-chat.md](phases/phase-7-function-calling-chat.md) and
[phases/phase-14-agui-streaming.md](phases/phase-14-agui-streaming.md)):

- **Declarations:** `{"type": "function", "name", "description", "parameters": <JSON schema>}`, passed as `tools=[...]`.
- **Calls:** steps with `type == "function_call"`, plus `name`, `arguments` (a dict) and `id`.
  Gemini can request several calls in one step.
- **Streaming (`stream=True`):** the SDK yields `interaction.created`, then for each step `step.start` (index, type;
  a function call's name and id with empty arguments), `step.delta` pieces (`text`, `arguments_delta` JSON fragments,
  `thought_signature`, `thought_summary`) and `step.stop`, then `interaction.completed` (status and usage, **no steps**),
  or an `error` event. `GeminiStream` yields the `text` pieces and rebuilds the steps from the deltas, because the
  next request must resend them unchanged.
- **Results (stateless, `store=False`):** resend the whole history every time. That means the `user_input`, then
  every step Gemini returned **unchanged**, then one `{"type": "function_result", "name", "call_id", "is_error",
  "result": [{"type": "text", "text": "<json>"}]}` per call.
- **Automatic function calling** (the SDK running your Python functions for you) isn't available in the Interactions
  API, so `modules/assistant/agent.py` runs the loop itself.
- **Thinking level:** `generation_config={"thinking_level": "minimal" | "low" | "medium" | "high" | "xhigh"}`. The agent
  uses `low`; with deeper thinking, a single step took 40–60+ s in testing.

## Conversation memory and cost

Gemini remembers nothing between requests, and with `store=False` Google keeps nothing either. So `/chat` stores each
thread's steps in the `ChatMessage` table and resends the **last 10 turns** with every new message
([phases/phase-8-memory.md](phases/phase-8-memory.md)). Every token of that history is billed on every request, and
again on every step of the agent loop, so the cap keeps long conversations from getting ever more expensive. The
console shows `tokens: N in, M out` for each step.

## Timeouts and retries

The client gives up on an attempt after **60 s** and makes **at most 2 attempts**, retrying **only 5xx errors**
(`HttpOptions(timeout=60_000, retry_options=HttpRetryOptions(attempts=2, http_status_codes=[500, 502, 503, 504]))`
in `core/llm.py`):
- The SDK's defaults (5 attempts, up to 60 s apart) made requests hang for many minutes while Gemini was down.
- The limit was 30 s in Phase 6, but function-calling steps can legitimately take 20–30 s.
- Google's quick "high demand" errors still fail fast; only a hung connection takes up to about 2 minutes.
- **Never retry 429 (quota used up).** The SDK retries 429 by default, and before retrying it sleeps for as long as
  Google's `retry-after-ms` header asks, with no upper limit and no timeout. With an exhausted quota that looked like a
  request hanging forever (found in Phase 14; D108). Now a 429 fails at once with Google's quota message.

## When something goes wrong

| What you see from `POST /ask` or `POST /parse` | Meaning | Where to look |
|---|---|---|
| `422` | The request body is invalid, e.g. an empty prompt or over 4000 characters | The `detail` field says which rule failed |
| `500 Internal Server Error` | Our setup is wrong: `GEMINI_API_KEY` or `GEMINI_MODEL` isn't set | The server terminal says which setting is missing |
| `502` with "API key not valid" | Gemini rejected the key | Re-copy the key into `.env`, then restart |
| `502` with a quota or rate-limit message | Free-tier limit reached | AI Studio rate-limit page; wait for the reset |
| `502` mentioning the model | The model isn't available to your key | Pick a free-tier model from the table above |
| `502` "experiencing high demand" (Google's 503) | The model is temporarily overloaded | Wait a few minutes, or switch `GEMINI_MODEL` (e.g. `gemini-4-hydrogen`) and restart |
| `502` "didn't match the expected shape" | Gemini's JSON didn't fit `ParsedExpense` | Rare with structured output; retry. If it repeats, the schema or descriptions need a look |
| `422` "There are no categories yet" (`/parse` only) | Nothing to pick a category from | Run `backend\seed.py` or add categories |

**500 vs 502:** a 500 means *our* server has a problem; a 502 means a service we depend on (Gemini) failed.

## Tokens, briefly

- A token is a chunk of text, about **4 characters** for Gemini; 100 tokens is roughly 60–80 English words.
- Input (your prompt), output (the answer) and the model's thinking are all counted.
- `/ask` caps prompts at 4000 characters (about 1000 tokens) to limit cost and abuse.
- Each response reports its usage (`interaction.usage`: `total_input_tokens`, `total_output_tokens`,
  `total_thought_tokens`, `total_tokens`). SpendWise doesn't show these yet.
