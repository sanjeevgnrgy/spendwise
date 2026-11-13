"""Tests for POST /parse and parse_expense. Gemini is replaced by a fake, so these run offline,
cost nothing, and always get the same answer."""

import json
from datetime import date
from decimal import Decimal

import pytest

from app.core import llm
from app.modules.assistant import parse

TODAY = date(2026, 11, 13)
FULL_ANSWER = {
    "amount": "450.50",
    "currency": "INR",
    "category": "Food",
    "merchant": "Swiggy",
    "spent_on": "2026-11-12",
    "payment_method": "upi",
    "note": "Dinner",
}


class FakeGemini:
    """Stands in for llm.ask_gemini_for_json. Set `.answer`; read `.calls` to see what was sent."""

    def __init__(self) -> None:
        self.answer: dict | str = FULL_ANSWER
        self.calls: list[dict] = []

    def __call__(self, prompt: str, schema: dict, system_instruction: str) -> str:
        self.calls.append({"prompt": prompt, "schema": schema, "system_instruction": system_instruction})
        return self.answer if isinstance(self.answer, str) else json.dumps(self.answer)


@pytest.fixture
def fake_gemini(monkeypatch) -> FakeGemini:
    fake = FakeGemini()
    # monkeypatch swaps the function for this one test and puts the real one back afterwards.
    monkeypatch.setattr(llm, "ask_gemini_for_json", fake)
    return fake


# ---------- parse_expense (no HTTP) ----------


def test_schema_sent_to_gemini_limits_category_and_allows_null_amount(fake_gemini):
    parse.parse_expense("Swiggy 450.50 yesterday", TODAY, ["Food", "Travel"])

    sent = fake_gemini.calls[0]
    assert sent["schema"]["properties"]["category"]["anyOf"][0]["enum"] == ["Food", "Travel"]
    assert sent["schema"]["properties"]["amount"]["type"] == ["string", "null"]
    assert sorted(sent["schema"]["required"]) == sorted(sent["schema"]["properties"])
    assert "2026-11-13" in sent["system_instruction"]
    assert sent["prompt"] == "Swiggy 450.50 yesterday"


def test_complete_note_is_parsed_with_nothing_missing(fake_gemini):
    parsed = parse.parse_expense("Swiggy 450.50 yesterday via GPay", TODAY, ["Food"])

    assert parsed.amount == Decimal("450.50")
    assert parsed.spent_on == date(2026, 11, 12)
    assert parse.missing_fields(parsed) == []


def test_note_without_an_amount_reports_amount_missing(fake_gemini):
    fake_gemini.answer = {**FULL_ANSWER, "amount": None}

    parsed = parse.parse_expense("Dinner at Swiggy yesterday", TODAY, ["Food"])

    assert parsed.amount is None
    assert parse.missing_fields(parsed) == ["amount"]


def test_category_outside_the_allowed_list_is_dropped(fake_gemini):
    fake_gemini.answer = {**FULL_ANSWER, "category": "Snacks"}

    parsed = parse.parse_expense("chips 50", TODAY, ["Food"])

    assert parsed.category is None
    assert "category" in parse.missing_fields(parsed)


def test_answer_in_the_wrong_shape_is_a_gemini_error(fake_gemini):
    fake_gemini.answer = "Sorry, I can't help with that."

    with pytest.raises(llm.GeminiError, match="didn't match the expected shape"):
        parse.parse_expense("anything", TODAY, ["Food"])


# ---------- POST /parse (HTTP) ----------


def test_post_parse_suggests_an_expense_but_saves_nothing(client, food, fake_gemini):
    response = client.post("/parse", json={"text": "Paid 450.50 at Swiggy yesterday via GPay"})

    assert response.status_code == 200
    assert response.json()["expense"]["amount"] == "450.50"
    assert response.json()["missing_fields"] == []
    assert client.get("/expenses").json() == []


def test_post_parse_without_any_categories_is_422(client, fake_gemini):
    response = client.post("/parse", json={"text": "Swiggy 450"})

    assert response.status_code == 422
    assert fake_gemini.calls == []  # Gemini wasn't even asked


def test_post_parse_when_gemini_fails_is_502(client, food, fake_gemini):
    fake_gemini.answer = "not json"

    assert client.post("/parse", json={"text": "Swiggy 450"}).status_code == 502


def test_post_ask_when_gemini_fails_is_502(client, monkeypatch):
    def broken(prompt):
        raise llm.GeminiError("API key not valid")

    monkeypatch.setattr(llm, "ask_gemini", broken)

    response = client.post("/ask", json={"prompt": "hi"})

    assert response.status_code == 502
    assert response.json() == {"detail": "API key not valid"}
