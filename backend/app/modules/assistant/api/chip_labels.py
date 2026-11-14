"""What each tool call's status chip says, in the request's language.

Adapter layer. agui_stream.py sends a chip's three texts in TOOL_CALL_START's metadata (protocol.ToolLabels), so the
browser shows them without knowing any tool names, and without translating them: they arrive already written in
the language the request asked for.
"""

from dataclasses import dataclass

from app.core.i18n import Language, text
from app.modules.assistant.agent.events import ToolIntent
from app.modules.assistant.api.protocol import ToolLabels
from app.modules.assistant.i18n import ChatText
from app.modules.mcp import ToolName


@dataclass(frozen=True)
class _ChipTexts:
    """The keys of one chip's three texts: while the tool runs, and after it worked or failed."""

    running: ChatText
    done: ChatText
    failed: ChatText

    def write(self, language: Language, **values: object) -> ToolLabels:
        """The three texts in `language`, with `values` filled in."""
        return ToolLabels(
            running=text(language, self.running, **values),
            done=text(language, self.done, **values),
            failed=text(language, self.failed, **values),
        )


# Each tool's own chip texts.
TOOL_CHIPS: dict[str, _ChipTexts] = {
    ToolName.ADD_EXPENSE: _ChipTexts(
        running=ChatText.CHIP_ADD_RUNNING, done=ChatText.CHIP_ADD_DONE, failed=ChatText.CHIP_ADD_FAILED
    ),
    ToolName.UPDATE_EXPENSE: _ChipTexts(
        running=ChatText.CHIP_UPDATE_RUNNING,
        done=ChatText.CHIP_UPDATE_DONE,
        failed=ChatText.CHIP_UPDATE_FAILED,
    ),
    ToolName.DELETE_EXPENSE: _ChipTexts(
        running=ChatText.CHIP_DELETE_RUNNING,
        done=ChatText.CHIP_DELETE_DONE,
        failed=ChatText.CHIP_DELETE_FAILED,
    ),
    ToolName.GET_EXPENSE: _ChipTexts(
        running=ChatText.CHIP_GET_RUNNING, done=ChatText.CHIP_GET_DONE, failed=ChatText.CHIP_GET_FAILED
    ),
    ToolName.LIST_EXPENSES: _ChipTexts(
        running=ChatText.CHIP_LIST_RUNNING,
        done=ChatText.CHIP_LIST_DONE,
        failed=ChatText.CHIP_LIST_FAILED,
    ),
    ToolName.GET_SUMMARY: _ChipTexts(
        running=ChatText.CHIP_SUMMARY_RUNNING,
        done=ChatText.CHIP_SUMMARY_DONE,
        failed=ChatText.CHIP_SUMMARY_FAILED,
    ),
}
# A delete in the web panel only looks the expense up and asks: a chip must never claim a delete.
APPROVAL_CHECK_CHIP = _ChipTexts(
    running=ChatText.CHIP_APPROVAL_RUNNING,
    done=ChatText.CHIP_APPROVAL_DONE,
    failed=ChatText.CHIP_APPROVAL_FAILED,
)
# A tool without texts of its own: its name, made readable ("get_summary" -> "get summary"), fills in {tool}.
ANY_TOOL_CHIP = _ChipTexts(
    running=ChatText.CHIP_TOOL_RUNNING, done=ChatText.CHIP_TOOL_DONE, failed=ChatText.CHIP_TOOL_FAILED
)


def labels_for(name: str, intent: ToolIntent, language: Language) -> ToolLabels:
    """What the chip for a tool call says, in `language`: an approval check's own texts, the tool's, or generic ones."""
    if intent == ToolIntent.APPROVAL_CHECK:
        return APPROVAL_CHECK_CHIP.write(language)
    chip = TOOL_CHIPS.get(name)
    if chip is not None:
        return chip.write(language)
    return ANY_TOOL_CHIP.write(language, tool=name.replace("_", " "))
