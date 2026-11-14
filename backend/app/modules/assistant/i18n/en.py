"""The assistant module's texts for people, in English: their keys, and the source every other language translates.

Part of the assistant module (i18n/). Only what a person reads: the cards and the expense form (a2ui/), the tool
chips (api/chip_labels.py), the replies the server writes itself (agent/agent.py, application/decisions.py) and the
errors a person is shown (a 422 or 502 problem's detail, or a RUN_ERROR's message). What the model reads (its
instruction, tool descriptions and results, the user's clicks as written into the conversation) stays plain English
where it's written. hi.py translates these; __init__.py registers the catalog.
"""

from enum import StrEnum

from app.core.i18n import Plural, TextValue


class ChatText(StrEnum):
    """The assistant module's texts, by key."""

    # Cards (a2ui/cards.py, a2ui/summary_card.py)
    EXPENSE_SAVED = "cards.expense.saved"
    EXPENSE_UPDATED = "cards.expense.updated"
    EXPENSE_DELETED = "cards.expense.deleted"
    EXPENSE_FOUND = "cards.expense.found"
    DELETE_TITLE = "cards.delete.title"
    DELETE_FOOTER = "cards.delete.footer"
    DELETE_APPROVE = "cards.delete.approve"
    DELETE_CANCEL = "cards.delete.cancel"
    DELETE_APPROVE_MESSAGE = "cards.delete.approveMessage"
    DELETE_CANCEL_MESSAGE = "cards.delete.cancelMessage"
    SUMMARY_TITLE = "cards.summary.title"
    SUMMARY_SPENT_IN = "cards.summary.spentIn"
    SUMMARY_NOTHING_BEFORE = "cards.summary.nothingSpentBefore"
    SUMMARY_SAME_AS = "cards.summary.sameAs"
    SUMMARY_CHANGE = "cards.summary.change"
    SUMMARY_TOP_CATEGORY = "cards.summary.topCategory"
    SUMMARY_TOP_SHARE = "cards.summary.topShare"
    SUMMARY_EVERYTHING_ELSE = "cards.summary.everythingElse"
    SUMMARY_EXPENSE_COUNT = "cards.summary.expenseCount"
    SUMMARY_NO_EXPENSES = "cards.summary.noExpenses"
    LIST_NONE = "cards.list.none"
    LIST_FOUND = "cards.list.found"
    LIST_ROW_DETAILS = "cards.list.rowDetails"
    LIST_MORE = "cards.list.more"
    # The expense form (a2ui/forms.py)
    FORM_TITLE = "form.title"
    FORM_AMOUNT = "form.amount"
    FORM_CATEGORY = "form.category"
    FORM_MERCHANT = "form.merchant"
    FORM_DATE = "form.date"
    FORM_PAID_WITH = "form.paidWith"
    FORM_NOTE = "form.note"
    FORM_SAVE = "form.save"
    # Tool chips (api/chip_labels.py): while running, then done or failed
    CHIP_ADD_RUNNING = "chips.addExpense.running"
    CHIP_ADD_DONE = "chips.addExpense.done"
    CHIP_ADD_FAILED = "chips.addExpense.failed"
    CHIP_UPDATE_RUNNING = "chips.updateExpense.running"
    CHIP_UPDATE_DONE = "chips.updateExpense.done"
    CHIP_UPDATE_FAILED = "chips.updateExpense.failed"
    CHIP_DELETE_RUNNING = "chips.deleteExpense.running"
    CHIP_DELETE_DONE = "chips.deleteExpense.done"
    CHIP_DELETE_FAILED = "chips.deleteExpense.failed"
    CHIP_GET_RUNNING = "chips.getExpense.running"
    CHIP_GET_DONE = "chips.getExpense.done"
    CHIP_GET_FAILED = "chips.getExpense.failed"
    CHIP_LIST_RUNNING = "chips.listExpenses.running"
    CHIP_LIST_DONE = "chips.listExpenses.done"
    CHIP_LIST_FAILED = "chips.listExpenses.failed"
    CHIP_SUMMARY_RUNNING = "chips.getSummary.running"
    CHIP_SUMMARY_DONE = "chips.getSummary.done"
    CHIP_SUMMARY_FAILED = "chips.getSummary.failed"
    CHIP_APPROVAL_RUNNING = "chips.approvalCheck.running"
    CHIP_APPROVAL_DONE = "chips.approvalCheck.done"
    CHIP_APPROVAL_FAILED = "chips.approvalCheck.failed"
    CHIP_TOOL_RUNNING = "chips.anyTool.running"
    CHIP_TOOL_DONE = "chips.anyTool.done"
    CHIP_TOOL_FAILED = "chips.anyTool.failed"
    # Replies the server writes itself (agent/agent.py, application/decisions.py)
    TOO_MANY_STEPS = "replies.tooManySteps"
    FORM_SHOWN = "replies.formShown"
    TOOLS_UNAVAILABLE = "replies.toolsUnavailable"
    STALE_APPROVAL = "replies.staleApproval"
    CANCELLED = "replies.cancelled"
    CHANGED_SINCE = "replies.changedSince"
    DELETED = "replies.deleted"
    DELETE_FAILED = "replies.deleteFailed"
    # Errors a person is shown
    RUN_FAILED = "errors.runFailed"
    EMPTY_ANSWER = "errors.emptyAnswer"
    WRONG_SHAPE = "errors.wrongShape"
    TOOLS_UNREACHABLE_IN_PROCESS = "errors.toolsUnreachableInProcess"
    TOOLS_UNREACHABLE_AT = "errors.toolsUnreachableAt"
    NO_USER_MESSAGE = "errors.noUserMessage"
    MESSAGE_LENGTH = "errors.messageLength"
    INVALID_ACTION = "errors.invalidAction"
    THREAD_ID_LENGTH = "errors.threadIdLength"
    FORM_TOO_LONG = "errors.formTooLong"


EN: dict[ChatText, TextValue] = {
    ChatText.EXPENSE_SAVED: "Expense saved",
    ChatText.EXPENSE_UPDATED: "Expense updated",
    ChatText.EXPENSE_DELETED: "Expense deleted",
    ChatText.EXPENSE_FOUND: "Expense",
    ChatText.DELETE_TITLE: "Delete this expense?",
    ChatText.DELETE_FOOTER: "Nothing is deleted unless you press Approve.",
    ChatText.DELETE_APPROVE: "Approve",
    ChatText.DELETE_CANCEL: "Cancel",
    # What a click on the button reads as in the chat; {ref} is the expense's "#14".
    ChatText.DELETE_APPROVE_MESSAGE: "Approve deleting {ref}",
    ChatText.DELETE_CANCEL_MESSAGE: "Cancel deleting {ref}",
    # {month} is "November 2026" in the title, "November" everywhere else on the card.
    ChatText.SUMMARY_TITLE: "Where your money went in {month}",
    ChatText.SUMMARY_SPENT_IN: "Spent in {month}",
    ChatText.SUMMARY_NOTHING_BEFORE: "Nothing spent in {month}",
    ChatText.SUMMARY_SAME_AS: "Same as {month}",
    # {change} is a signed percentage: "+12%", "-0.4%".
    ChatText.SUMMARY_CHANGE: "{change} vs {month}",
    ChatText.SUMMARY_TOP_CATEGORY: "Biggest category",
    # The biggest category's total, and its share of the month's.
    ChatText.SUMMARY_TOP_SHARE: "{amount} · {share}%",
    ChatText.SUMMARY_EVERYTHING_ELSE: "Everything else",
    ChatText.SUMMARY_EXPENSE_COUNT: Plural(one="{count} expense", other="{count} expenses"),
    ChatText.SUMMARY_NO_EXPENSES: "No expenses in {month}",
    ChatText.LIST_NONE: "No matching expenses",
    ChatText.LIST_FOUND: Plural(one="Found {count} expense", other="Found {count} expenses"),
    ChatText.LIST_ROW_DETAILS: "{ref} · {category} · {date}",
    ChatText.LIST_MORE: "Showing the newest {shown} of {total}",
    ChatText.FORM_TITLE: "Add an expense",
    ChatText.FORM_AMOUNT: "Amount (₹)",
    ChatText.FORM_CATEGORY: "Category",
    ChatText.FORM_MERCHANT: "Merchant",
    ChatText.FORM_DATE: "Date",
    ChatText.FORM_PAID_WITH: "Paid with",
    ChatText.FORM_NOTE: "Note (optional)",
    ChatText.FORM_SAVE: "Save",
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
    ChatText.TOO_MANY_STEPS: (
        "Sorry, that took too many steps, so I stopped. Could you try a simpler or more specific request?"
    ),
    ChatText.FORM_SHOWN: "Please check the details in the form and press Save.",
    ChatText.TOOLS_UNAVAILABLE: (
        "Sorry, I can't reach the expense tools right now, so I can't look up or change anything. "
        "Please try again in a moment."
    ),
    # {count} is how many minutes a delete card works for (approvals.TTL_MINUTES).
    ChatText.STALE_APPROVAL: Plural(
        one="That card can't be used any more: it was already answered, or it's more than {count} minute old. "
        "Ask me again if you still want to delete the expense.",
        other="That card can't be used any more: it was already answered, or it's more than {count} minutes old. "
        "Ask me again if you still want to delete the expense.",
    ),
    ChatText.CANCELLED: "Okay, I won't delete {ref}. Nothing was changed.",
    ChatText.CHANGED_SINCE: (
        "I couldn't confirm that expense {ref} is still what the card showed (it changed, it's gone, "
        "or the tools are unreachable), so I didn't delete it. Ask me again to see it as it is now."
    ),
    ChatText.DELETED: "Done: expense {ref} is deleted.",
    # {error} is the tool's own message (English, from the MCP server), e.g. a version conflict.
    ChatText.DELETE_FAILED: (
        "I couldn't delete {ref} just now ({error}). Nothing was deleted; ask me again in a moment."
    ),
    # All a person is told about a bug in a run: the details go to the server log only.
    ChatText.RUN_FAILED: "Something went wrong on the server. The server log has the details.",
    ChatText.EMPTY_ANSWER: "The model returned neither text nor a tool call.",
    # {error} is Pydantic's explanation, in English.
    ChatText.WRONG_SHAPE: "The model's answer didn't match the expected shape: {error}",
    ChatText.TOOLS_UNREACHABLE_IN_PROCESS: "Could not reach the expense tools (this app's MCP server)",
    ChatText.TOOLS_UNREACHABLE_AT: "Could not reach the expense tools ({url})",
    ChatText.NO_USER_MESSAGE: "The run has no user message to answer.",
    ChatText.MESSAGE_LENGTH: "The message must be 1 to {max} characters long.",
    ChatText.INVALID_ACTION: "The button's action isn't valid.",
    ChatText.THREAD_ID_LENGTH: "threadId must be 1 to {max} characters long.",
    ChatText.FORM_TOO_LONG: "The form's values must be under {max} characters in total.",
}
