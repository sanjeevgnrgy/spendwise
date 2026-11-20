"""Pieces for the JSON schemas a model answers in (structured output): part of the LLM port (core layer).

Shared by every structured-output use case: the assistant's ExpenseParser (/parse) and the receipt agent's
ReceiptReader (agents/receipt/reader.py, D196). A schema is behaviour (the model reads it), so a piece both use is
defined once, here.
"""

import copy
from decimal import Decimal
from typing import Annotated, Any

from pydantic import WithJsonSchema

# An amount the model writes as a string, e.g. "1250.50", or null. The schema has no decimal type, and a JSON
# number could be read as a float; Pydantic turns the string into an exact Decimal.
DecimalText = Annotated[Decimal | None, WithJsonSchema({"type": ["string", "null"]})]


def restrict_to_choices(schema: dict[str, Any], field: str, choices: list[str]) -> dict[str, Any]:
    """A copy of `schema` where `field` may only be one of `choices`, or null; its description is kept.

    For a value the model must pick from a list known only while the app runs (the category names): with an enum,
    it can't answer one that isn't there. With no choices at all, the field can only be null. `schema` itself is
    left unchanged, so a cached one can be passed in.
    """
    restricted = copy.deepcopy(schema)
    properties = restricted["properties"]
    allowed: list[dict[str, Any]] = [{"type": "string", "enum": choices}] if choices else []
    properties[field] = {"anyOf": [*allowed, {"type": "null"}], "description": properties[field]["description"]}
    return restricted
