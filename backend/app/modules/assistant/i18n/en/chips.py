"""The assistant's texts in English: the tool chips (api/chip_labels.py): while a tool runs, then done or failed.

Part of the assistant module (i18n/): the source every other language translates. The keys are in keys.py.
"""

from app.core.i18n import TextValue
from app.modules.assistant.i18n.keys import ChatText

CHIPS: dict[ChatText, TextValue] = {
    ChatText.CHIP_ADD_RUNNING: "Saving expense…",
    ChatText.CHIP_ADD_DONE: "Expense saved",
    ChatText.CHIP_ADD_FAILED: "Couldn't save expense",
    ChatText.CHIP_UPDATE_RUNNING: "Updating expense…",
    ChatText.CHIP_UPDATE_DONE: "Expense updated",
    ChatText.CHIP_UPDATE_FAILED: "Couldn't update expense",
    ChatText.CHIP_DELETE_RUNNING: "Deleting expense…",
    ChatText.CHIP_DELETE_DONE: "Expense deleted",
    ChatText.CHIP_DELETE_FAILED: "Couldn't delete expense",
    ChatText.CHIP_GET_RUNNING: "Looking up the expense…",
    ChatText.CHIP_GET_DONE: "Found the expense",
    ChatText.CHIP_GET_FAILED: "Couldn't find the expense",
    ChatText.CHIP_LIST_RUNNING: "Looking up expenses…",
    ChatText.CHIP_LIST_DONE: "Looked up expenses",
    ChatText.CHIP_LIST_FAILED: "Couldn't look up expenses",
    ChatText.CHIP_SUMMARY_RUNNING: "Adding up the month…",
    ChatText.CHIP_SUMMARY_DONE: "Added up the month",
    ChatText.CHIP_SUMMARY_FAILED: "Couldn't add up the month",
    # A delete in the web panel only looks the expense up and asks: never a claim that it was deleted.
    ChatText.CHIP_APPROVAL_RUNNING: "Checking the expense…",
    ChatText.CHIP_APPROVAL_DONE: "Waiting for your OK",
    ChatText.CHIP_APPROVAL_FAILED: "Couldn't find the expense",
    # A tool without texts of its own; {tool} is its name, made readable ("get summary").
    ChatText.CHIP_TOOL_RUNNING: "Running {tool}…",
    ChatText.CHIP_TOOL_DONE: "Ran {tool}",
    ChatText.CHIP_TOOL_FAILED: "{tool} failed",
    # Reading an attached receipt: the receipt agent's step (application/receipt_turn.py).
    ChatText.CHIP_RECEIPT_RUNNING: "Asking the receipt agent…",
    ChatText.CHIP_RECEIPT_DONE: "Receipt read",
    ChatText.CHIP_RECEIPT_FAILED: "Couldn't read the receipt",
    # Shown after a chip's text when a remote agent did the work: {task} is the start of its A2A task id.
    ChatText.CHIP_TASK: "A2A task {task}",
    # The same, for a task that stopped to ask the person something (the reply asks it).
    ChatText.CHIP_TASK_WAITING: "A2A task {task} · waiting for your answer",
    # The model reading one of SpendWise's skills (D208).
    ChatText.CHIP_SKILL_RUNNING: "Reading a skill…",
    ChatText.CHIP_SKILL_DONE: "Read a skill",
    ChatText.CHIP_SKILL_FAILED: "Couldn't find that skill",
    ChatText.CHIP_REPORT_RUNNING: "Making the month's report…",
    ChatText.CHIP_REPORT_DONE: "Made the month's report",
    ChatText.CHIP_REPORT_FAILED: "Couldn't make the month's report",
    ChatText.CHIP_GET_BUDGETS_RUNNING: "Checking your budgets…",
    ChatText.CHIP_GET_BUDGETS_DONE: "Checked your budgets",
    ChatText.CHIP_GET_BUDGETS_FAILED: "Couldn't check your budgets",
    ChatText.CHIP_SET_BUDGET_RUNNING: "Setting the budget…",
    ChatText.CHIP_SET_BUDGET_DONE: "Budget set",
    ChatText.CHIP_SET_BUDGET_FAILED: "Couldn't set the budget",
    # The agents the model hands requests to (delegation/, D206).
    ChatText.CHIP_INSIGHTS_RUNNING: "Asking the insights agent…",
    ChatText.CHIP_INSIGHTS_DONE: "Insights agent answered",
    ChatText.CHIP_INSIGHTS_FAILED: "The insights agent couldn't answer",
    ChatText.CHIP_CURRENCY_RUNNING: "Asking the currency agent…",
    ChatText.CHIP_CURRENCY_DONE: "Currency agent answered",
    ChatText.CHIP_CURRENCY_FAILED: "The currency agent couldn't answer",
}
