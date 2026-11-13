# Phase 2: First Gemini call

> **Later changes:**
> **Refactor (after Phase 18):** `POST /ask` was removed: it sent any prompt to Gemini, an open proxy to your quota.
> `core/llm.py` became `core/llm/`, a provider-neutral port with a Gemini adapter. See
> [refactor-architecture.md](refactor-architecture.md).

**Goal:** `POST /ask` takes `{"prompt": "..."}` and returns Gemini's answer, with the API key and model read from `.env`.

> **Later changes:** in Phase 3, `ask_gemini` moved to `backend/app/core/llm.py`, `/ask` moved to
> `backend/app/modules/assistant/`, and `.env` is read by pydantic-settings instead of `python-dotenv`.
> The model is now `gemini-3.8-flash`. After Phase 4, the project moved from `spendwise/` to the repo root,
> so `spendwise/.env` below is now `.env` in the project folder.

## Concepts

- **Model:** a program trained on huge amounts of text that predicts a good reply to what you send it.
  Different models trade speed, cost and quality. Each has an ID such as `gemini-3.8-flash`. SpendWise reads
  the ID from `.env`, so you can switch models without touching code.
- **Prompt:** the text you send. It's your whole instruction, and the model only knows what's in it.
  A vague prompt gets a vague answer.
- **Token:** the unit a model reads and writes in, a chunk of a word. For Gemini, a token is about 4 characters
  (100 tokens is roughly 60–80 English words). Billing, speed and limits are all counted in tokens: input,
  output and the model's thinking.
- **Why the key lives in `.env`:** the API key is like the PIN for your Gemini quota and billing. Anyone who
  has it can spend your quota. Code goes to GitHub; `.env` is git-ignored and stays on your machine. Each
  person or server uses its own key with the same code.
- **Request body:** a `POST` carries JSON in its body. A Pydantic model (`AskRequest`) checks the JSON before
  your function runs; invalid input gets an automatic `422`.

**Analogy:** calling an expert on a phone line that's charged by the second. The model is the expert, the
prompt is your question, tokens are the seconds on the meter, and the API key is your account PIN. You keep
the PIN in your wallet (`.env`), not on the shared whiteboard (the repo).

## Checked before coding

- **Which API:** Google's docs now recommend the **Interactions API** (`client.interactions.create`) for new
  projects; `generate_content` is legacy but fully supported. → [decisions.md](../decisions.md) D6
- **`store=False`:** by default, the Interactions API keeps prompts and answers on Google's servers. → D7
- **Errors:** a test call with a wrong key showed the SDK raises an error class that is only available from a
  private module. → D8
- **Models and the free tier:** see [gemini.md](../gemini.md). → D10, D11

## What was built

- `requirements.txt`: added `google-genai`, `python-dotenv`, `pydantic` (pinned).
- `.env` (git-ignored) and `.env.example`: `GEMINI_API_KEY`, `GEMINI_MODEL`.
- `ask_gemini(prompt) -> str` in its own file, the only code that talks to Gemini:

```python
interaction = client.interactions.create(model=model, input=prompt, store=False)
if not interaction.output_text:
    raise GeminiError("Gemini returned no text.")
return interaction.output_text
```

- `POST /ask`:

```python
class AskRequest(BaseModel):
    # The upper limit matters because every character is sent to Gemini and paid for as tokens.
    prompt: str = Field(min_length=1, max_length=4000)


@router.post("/ask")
def ask(body: AskRequest) -> AskResponse:
    # A plain `def`, not `async def`: the Gemini call blocks while it waits, and FastAPI
    # runs plain functions in a worker thread so other requests aren't stuck behind it.
    try:
        answer = service.answer(body.prompt)
    except GeminiError as exc:
        # 502 means "a service we depend on failed", which is different from a bug here (500).
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return AskResponse(answer=answer)
```

## Run it

1. Paste your key into `spendwise\.env` after `GEMINI_API_KEY=`.
2. Restart the server (`.env` is only read at startup): Ctrl+C, then `.\run.ps1`.

## Test it by hand

In `/docs`, open **POST /ask** → **Try it out**, or from PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/ask -ContentType "application/json" -Body '{"prompt": "Give me one tip to save money on groceries."}'
```

| Situation | Response |
|---|---|
| Key set correctly | `200` with `{"answer": "..."}`; the wording varies each time |
| Empty prompt | `422`, "String should have at least 1 character" |
| Key missing | `500`; the terminal shows `GEMINI_API_KEY is not set. Add it to spendwise/.env ...` |
| Wrong key | `502`, with Google's "API key not valid" in `detail` |

## Check your understanding

**1. A wrong key gives 502 but a missing key gives 500. What's different, and why keep them apart?**

<details><summary>Answer</summary>

A **missing** key is our own misconfiguration: our server can't do its job, so `500 Internal Server Error`.
A **wrong** key means we reached Gemini and Gemini refused: the service we depend on failed, so
`502 Bad Gateway`. Keeping them apart tells you where to look (our config and logs vs. Google's side:
key, quota, model) and lets clients or monitoring react differently, e.g. retry a 502 later.
</details>

**2. `max_length=4000` characters is about how many tokens? Why cap it at all?**

<details><summary>Answer</summary>

About **1000 tokens** (roughly 4 characters per token). The cap limits cost and quota use per request, stops
someone sending huge text to burn your quota, keeps responses fast, and stays well within the model's limits.
</details>

**3. If you pushed the repo to GitHub, where would your key be, why wouldn't it be uploaded, and how would a
teammate know what to put in their own copy?**

<details><summary>Answer</summary>

The key is only in `spendwise/.env`. `.gitignore` lists `.env`, so git never tracks it. A teammate copies
`.env.example`, which is committed and lists the setting names with no secret values, to `.env` and fills in
their own key.
</details>
