"""Names on the wire between this module and the web app, beyond what AG-UI itself defines.

The AG-UI adapter uses them: agui_request.py to read a run (a button click, the data version),
agui_stream.py to write events (the custom event's name, metadata keys, chip labels). Each name is defined
once, here, instead of typed as a string wherever it's needed.

The web app gets these same values from generated code (backend/scripts/export_contracts.py writes
web/src/shared/api/contracts.gen.ts), so the two sides can't drift apart.
"""

from enum import StrEnum

from pydantic import BaseModel


# The names this app gives AG-UI's CUSTOM events (a CUSTOM event is a name plus any JSON value).
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


# Sent in TOOL_CALL_START's metadata (MetadataKey.LABELS), so the browser can show all three texts
# without knowing any tool names. chip_labels.labels_for writes them, in the request's language.
class ToolLabels(BaseModel):
    """What a tool's status chip says while it runs, and after it worked or failed."""

    running: str
    done: str
    failed: str
