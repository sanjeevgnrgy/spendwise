"""Tests for the agent loop and POST /chat. Gemini is replaced by a script of canned replies, so each
test controls exactly what the "model" does, step by step, with no network or API key."""

import copy
import logging
from datetime import date
from types import SimpleNamespace

import pytest
from google.genai import interactions

from app.core import llm
from app.modules import expenses
from app.modules.assistant import agent

TODAY = date(2026, 11, 13)


def calls(*tool_calls: tuple[str, dict]) -> SimpleNamespace:
    """A fake Gemini reply that asks to run these tools."""
    steps = [
        interactions.FunctionCallStep.model_validate(
            {"type": "function_call", "id": f"call_{i}", "name": name, "arguments": arguments}
        )
        for i, (name, arguments) in enumerate(tool_calls)
    ]
    return SimpleNamespace(steps=steps, output_text=None)


def text(reply: str) -> SimpleNamespace:
    """A fake Gemini reply that answers in text (which ends the loop)."""
    return SimpleNamespace(steps=[], output_text=reply)


class ScriptedGemini:
    """Stands in for llm.ask_gemini_with_tools: returns the given replies in order, and records each request."""

    def __init__(self, *replies: SimpleNamespace) -> None:
        self.replies = list(replies)
        self.requests: list[list[dict]] = []

    def __call__(self, history, tools, system_instruction, thinking_level=None):
        self.requests.append(copy.deepcopy(history))
        return self.replies.pop(0)


@pytest.fixture
def script(monkeypatch):
    def install(*replies: SimpleNamespace) -> ScriptedGemini:
        fake = ScriptedGemini(*replies)
        monkeypatch.setattr(llm, "ask_gemini_with_tools", fake)
        return fake

    return install


ADD_SWIGGY = {
    "amount": "450.50",
    "category": "Food",
    "merchant": "Swiggy",
    "spent_on": "2026-11-12",
    "payment_method": "upi",
}


# ---------- tool declarations ----------


def test_declarations_are_built_from_the_tool_signatures():
    add = next(d for d in agent.DECLARATIONS if d["name"] == "add_expense")

    assert add["type"] == "function"
    assert "ask the user" in add["description"]
    assert add["parameters"]["required"] == ["amount", "category", "merchant", "spent_on", "payment_method"]
    assert add["parameters"]["properties"]["amount"]["type"] == "string"
    assert "session" not in add["parameters"]["properties"]


# ---------- the loop ----------


def test_runs_a_tool_then_answers(session, food, script):
    gemini = script(calls(("add_expense", ADD_SWIGGY)), text("Saved ₹450.50 at Swiggy."))

    result = agent.run(session, "Swiggy 450.50 yesterday via GPay, food", TODAY)

    assert result.reply == "Saved ₹450.50 at Swiggy."
    assert [(c.name, c.ok) for c in result.tool_calls] == [("add_expense", True)]
    assert [e.merchant for e in expenses.list_expenses(session)] == ["Swiggy"]
    # The second request carried the whole conversation: the message, Gemini's call, and our result.
    assert [s["type"] for s in gemini.requests[1]] == ["user_input", "function_call", "function_result"]
    assert gemini.requests[1][2]["call_id"] == "call_0"


def test_stops_after_max_steps(session, food, script):
    gemini = script(*[calls(("list_expenses", {}))] * agent.MAX_STEPS)

    result = agent.run(session, "keep listing forever", TODAY)

    assert len(gemini.requests) == agent.MAX_STEPS
    assert len(result.tool_calls) == agent.MAX_STEPS
    assert "too many steps" in result.reply


def test_a_failing_tool_call_goes_back_to_the_model_as_an_error(session, food, script):
    gemini = script(calls(("add_expense", {**ADD_SWIGGY, "category": "Snacks"})), text("Which category?"))

    result = agent.run(session, "chips 50", TODAY)

    assert result.tool_calls[0].ok is False
    sent_back = gemini.requests[1][-1]
    assert sent_back["is_error"] is True
    assert "Unknown category 'Snacks'" in sent_back["result"][0]["text"]
    assert expenses.list_expenses(session) == []


@pytest.mark.parametrize(
    ("tool_call", "expected_error"),
    [
        (("no_such_tool", {}), "There is no tool called no_such_tool"),
        (("get_summary", {"month": "2026-11", "colour": "red"}), "Wrong arguments for get_summary"),
    ],
)
def test_unknown_tools_and_arguments_are_reported_not_crashed(session, script, tool_call, expected_error):
    gemini = script(calls(tool_call), text("Sorry."))

    agent.run(session, "hi", TODAY)

    assert expected_error in gemini.requests[1][-1]["result"][0]["text"]


def test_delete_needs_confirmation(session, food, script):
    saved = expenses.create_expense(
        session,
        expenses.ExpenseCreate(amount="10", category_id=food.id, merchant="Chai", spent_on=TODAY, payment_method="cash"),
    )

    script(calls(("delete_expense", {"expense_id": saved.id})), text("Delete Chai ₹10? Please confirm."))
    agent.run(session, "delete the chai expense", TODAY)
    assert expenses.get_expense(session, saved.id)  # still there: no confirmation yet

    script(calls(("delete_expense", {"expense_id": saved.id, "confirmed": True})), text("Deleted."))
    agent.run(session, f"Yes, delete expense {saved.id}", TODAY)
    assert expenses.list_expenses(session) == []


def test_every_tool_call_is_logged(session, food, script, caplog):
    script(calls(("list_expenses", {"merchant": "swiggy"})), text("None found."))

    with caplog.at_level(logging.INFO, logger="spendwise.agent"):
        agent.run(session, "what did I spend at Swiggy?", TODAY)

    assert 'tool call: list_expenses({"merchant": "swiggy"})' in caplog.text
    assert "step 2/5" in caplog.text


# ---------- POST /chat ----------


def test_post_chat_returns_the_reply_and_the_tools_called(client, food, script):
    script(calls(("add_expense", ADD_SWIGGY)), text("Saved ₹450.50 at Swiggy."))

    response = client.post("/chat", json={"message": "Swiggy 450.50 yesterday via GPay"})

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Saved ₹450.50 at Swiggy."
    assert body["tool_calls"] == [{"name": "add_expense", "arguments": ADD_SWIGGY, "ok": True}]
    assert len(client.get("/expenses").json()) == 1
