"""Names on the wire between this module and the web app, beyond what AG-UI itself defines.

The web app gets these same values from generated code (backend/scripts/export_contracts.py writes
web/src/shared/api/contracts.gen.ts), so the two sides can't drift apart.
"""

from enum import StrEnum

from pydantic import BaseModel


class CustomEventName(StrEnum):
    # A2UI has no event of its own in AG-UI, so cards and forms travel in AG-UI's CUSTOM event.
    A2UI = "a2ui"


class MetadataKey(StrEnum):
    """Keys in an AG-UI event's `metadata` (the slot every event has for extra data)."""

    OK = "ok"  # TOOL_CALL_RESULT: did the tool succeed?
    LABELS = "labels"  # TOOL_CALL_START: what the chip says (ToolLabels)
    SOURCE = "source"  # CUSTOM a2ui form: "model" or "fallback"


# Nothing official says how an A2UI action travels over AG-UI, so the client puts the A2UI `action`
# message in RunAgentInput.forwardedProps (AG-UI's field for extra data from the client) under this key.
FORWARDED_A2UI_ACTION = "a2uiAction"
# AG-UI shared state: the client sends {"dataVersion": n} with each run and gets it back, raised,
# after a tool changed data. A new number is what makes the pages reload.
STATE_DATA_VERSION = "dataVersion"


class ToolLabels(BaseModel):
    """What a tool's status chip says while it runs, and after it worked or failed."""

    running: str
    done: str
    failed: str
