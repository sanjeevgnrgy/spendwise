from app.core.llm import ask_gemini


def answer(prompt: str) -> str:
    # Just a pass-through today. The orchestrator logic (tools, context, safety) grows
    # here in later phases, keeping the router free of business logic.
    return ask_gemini(prompt)
