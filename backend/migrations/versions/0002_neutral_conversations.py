"""Conversations move to their own module, stored in provider-neutral messages; approvals get a table.

- chatmessage becomes conversation_message, and every stored step is converted from Gemini's wire
  format to SpendWise's own message format (core/llm/messages.py), so the history no longer depends on
  one provider. Thought signatures are kept, as opaque Gemini data.
- pending_approval: the delete cards waiting for Approve, until now kept in memory.

The conversion is written out here, not imported from the app: a migration must keep doing exactly
what it did, even after the app's code changes.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-13
"""

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GEMINI = "gemini"


def _text(parts: list[dict[str, Any]] | None) -> str:
    return "".join(part.get("text", "") for part in parts or [] if part.get("type") == "text")


def _to_neutral(step: dict[str, Any]) -> dict[str, Any] | None:
    match step.get("type"):
        case "user_input":
            return {"kind": "user_text", "text": _text(step.get("content"))}
        case "model_output":
            return {"kind": "assistant_text", "text": _text(step.get("content"))}
        case "function_call":
            return {"kind": "tool_call", "call_id": step["id"], "name": step["name"], "arguments": step.get("arguments") or {}}
        case "function_result":
            return {
                "kind": "tool_result",
                "call_id": step["call_id"],
                "name": step["name"],
                "output": _text(step.get("result")),
                "is_error": bool(step.get("is_error")),
            }
        case "thought":
            opaque = {key: value for key, value in step.items() if key != "type" and value is not None}
            return {"kind": "reasoning", "provider": GEMINI, "opaque": opaque}
    return None  # a step type we never used: dropped


def _to_gemini(message: dict[str, Any]) -> dict[str, Any] | None:
    content = lambda text: [{"type": "text", "text": text}]  # noqa: E731
    match message.get("kind"):
        case "user_text":
            return {"type": "user_input", "content": content(message["text"])}
        case "assistant_text":
            return {"type": "model_output", "content": content(message["text"])}
        case "tool_call":
            return {"type": "function_call", "id": message["call_id"], "name": message["name"], "arguments": message["arguments"]}
        case "tool_result":
            return {
                "type": "function_result",
                "call_id": message["call_id"],
                "name": message["name"],
                "is_error": message["is_error"],
                "result": content(message["output"]),
            }
        case "reasoning" if message.get("provider") == GEMINI:
            return {"type": "thought", **message["opaque"]}
    return None


def _convert(table: str, convert: Any, kind_of: Any) -> None:
    connection = op.get_bind()
    rows = connection.execute(sa.text(f"SELECT id, content FROM {table}")).fetchall()
    for row_id, raw in rows:
        converted = convert(json.loads(raw) if isinstance(raw, str) else raw)
        if converted is None:
            connection.execute(sa.text(f"DELETE FROM {table} WHERE id = :id"), {"id": row_id})
        else:
            connection.execute(
                sa.text(f"UPDATE {table} SET kind = :kind, content = :content WHERE id = :id"),
                {"kind": kind_of(converted), "content": json.dumps(converted), "id": row_id},
            )


def upgrade() -> None:
    op.drop_index("ix_chatmessage_thread_id", table_name="chatmessage")
    op.rename_table("chatmessage", "conversation_message")
    op.create_index("ix_conversation_message_thread_id", "conversation_message", ["thread_id"])
    _convert("conversation_message", _to_neutral, lambda message: message["kind"])

    op.create_table(
        "pending_approval",
        sa.Column("approval_id", sa.String(length=64), primary_key=True),
        sa.Column("thread_id", sa.String(length=32), nullable=False),
        sa.Column("expense", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_pending_approval_thread_id", "pending_approval", ["thread_id"])
    op.create_index("ix_pending_approval_created_at", "pending_approval", ["created_at"])


def downgrade() -> None:
    op.drop_table("pending_approval")
    _convert("conversation_message", _to_gemini, lambda step: step["type"])
    op.drop_index("ix_conversation_message_thread_id", table_name="conversation_message")
    op.rename_table("conversation_message", "chatmessage")
    op.create_index("ix_chatmessage_thread_id", "chatmessage", ["thread_id"])
