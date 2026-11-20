"""What each tool call's status chip says, in the request's language.

Adapter layer. agui_stream.py sends a chip's three texts in TOOL_CALL_START's metadata (protocol.ToolLabels), so the
browser shows them without knowing any tool names, and without translating them: they arrive already written in
the language the request asked for. task_detail writes what a chip adds when a remote agent did the work (D200).
"""

from dataclasses import dataclass

from app.core.i18n import Language, text
from app.modules.assistant.agent.events import ToolIntent
from app.modules.assistant.api.protocol import ToolLabels
from app.modules.assistant.delegation import ASK_CURRENCY, ASK_INSIGHTS
from app.modules.assistant.i18n import ChatText
from app.modules.assistant.receipt_agent.port import READ_RECEIPT
from app.modules.assistant.skills import LOAD_SKILL
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
    # Not MCP tools: the agents the model delegates to (delegation/, D206), each with its own texts.
    ASK_INSIGHTS: _ChipTexts(
        running=ChatText.CHIP_INSIGHTS_RUNNING,
        done=ChatText.CHIP_INSIGHTS_DONE,
        failed=ChatText.CHIP_INSIGHTS_FAILED,
    ),
    ASK_CURRENCY: _ChipTexts(
        running=ChatText.CHIP_CURRENCY_RUNNING,
        done=ChatText.CHIP_CURRENCY_DONE,
        failed=ChatText.CHIP_CURRENCY_FAILED,
    ),
    # Not an MCP tool: the model reading one of SpendWise's skills (skills/, D208).
    LOAD_SKILL: _ChipTexts(
        running=ChatText.CHIP_SKILL_RUNNING, done=ChatText.CHIP_SKILL_DONE, failed=ChatText.CHIP_SKILL_FAILED
    ),
    # Not an MCP tool: the receipt agent reading an attached receipt (application/receipt_turn.py).
    READ_RECEIPT: _ChipTexts(
        running=ChatText.CHIP_RECEIPT_RUNNING,
        done=ChatText.CHIP_RECEIPT_DONE,
        failed=ChatText.CHIP_RECEIPT_FAILED,
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


# How much of a remote agent's task id the chip shows: enough to find the task in the agent's log.
TASK_ID_SHOWN = 8


def task_detail(task_id: str, language: Language, waiting: bool = False) -> str:
    """What a chip shows after its own text for work a remote agent did: "A2A task 3f2a9c1e", or, if the task is
    waiting for the person's answer, "A2A task 3f2a9c1e · waiting for your answer", in `language`."""
    key = ChatText.CHIP_TASK_WAITING if waiting else ChatText.CHIP_TASK
    return text(language, key, task=task_id[:TASK_ID_SHOWN])
