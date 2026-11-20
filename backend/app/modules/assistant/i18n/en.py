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
    # The monthly report card (a2ui/report_card.py, D209)
    REPORT_TITLE = "cards.report.title"
    REPORT_DAILY_AVERAGE = "cards.report.dailyAverage"
    REPORT_OVER_DAYS = "cards.report.overDays"
    REPORT_CATEGORY_DETAILS = "cards.report.categoryDetails"
    REPORT_BIGGEST = "cards.report.biggest"
    REPORT_DOWNLOAD_CSV = "cards.report.downloadCsv"
    REPORT_DOWNLOAD_MARKDOWN = "cards.report.downloadMarkdown"
    # The budget card (a2ui/budget_card.py) and the budget alerts on an expense card (Phase 27, D211)
    BUDGETS_TITLE = "cards.budgets.title"
    BUDGETS_NONE = "cards.budgets.none"
    BUDGET_OVERALL = "cards.budgets.overall"
    BUDGET_NO_OVERALL = "cards.budgets.noOverall"
    BUDGET_SPENT_OF = "cards.budgets.spentOf"
    BUDGET_USED = "cards.budgets.used"
    BUDGET_OVER_BY = "cards.budgets.overBy"
    BUDGET_ELAPSED = "cards.budgets.elapsed"
    BUDGET_STATE_ON_TRACK = "cards.budgets.state.onTrack"
    BUDGET_STATE_NEAR_LIMIT = "cards.budgets.state.nearLimit"
    BUDGET_STATE_OVER_LIMIT = "cards.budgets.state.overLimit"
    BUDGET_ALERT_NEAR = "cards.budgets.alertNear"
    BUDGET_ALERT_OVER = "cards.budgets.alertOver"
    LIST_NONE = "cards.list.none"
    LIST_FOUND = "cards.list.found"
    LIST_ROW_DETAILS = "cards.list.rowDetails"
    LIST_MORE = "cards.list.more"
    # The expense form (a2ui/forms.py)
    FORM_TITLE = "form.title"
    FORM_AMOUNT = "form.amount"
    FORM_CURRENCY = "form.currency"
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
    CHIP_RECEIPT_RUNNING = "chips.readReceipt.running"
    CHIP_RECEIPT_DONE = "chips.readReceipt.done"
    CHIP_RECEIPT_FAILED = "chips.readReceipt.failed"
    CHIP_TASK = "chips.task"
    CHIP_TASK_WAITING = "chips.taskWaiting"
    CHIP_SKILL_RUNNING = "chips.loadSkill.running"
    CHIP_SKILL_DONE = "chips.loadSkill.done"
    CHIP_SKILL_FAILED = "chips.loadSkill.failed"
    CHIP_REPORT_RUNNING = "chips.getMonthlyReport.running"
    CHIP_REPORT_DONE = "chips.getMonthlyReport.done"
    CHIP_REPORT_FAILED = "chips.getMonthlyReport.failed"
    CHIP_GET_BUDGETS_RUNNING = "chips.getBudgets.running"
    CHIP_GET_BUDGETS_DONE = "chips.getBudgets.done"
    CHIP_GET_BUDGETS_FAILED = "chips.getBudgets.failed"
    CHIP_SET_BUDGET_RUNNING = "chips.setBudget.running"
    CHIP_SET_BUDGET_DONE = "chips.setBudget.done"
    CHIP_SET_BUDGET_FAILED = "chips.setBudget.failed"
    CHIP_INSIGHTS_RUNNING = "chips.askInsights.running"
    CHIP_INSIGHTS_DONE = "chips.askInsights.done"
    CHIP_INSIGHTS_FAILED = "chips.askInsights.failed"
    CHIP_CURRENCY_RUNNING = "chips.askCurrency.running"
    CHIP_CURRENCY_DONE = "chips.askCurrency.done"
    CHIP_CURRENCY_FAILED = "chips.askCurrency.failed"
    # Replies the server writes itself (agent/agent.py, application/decisions.py)
    TOO_MANY_STEPS = "replies.tooManySteps"
    FORM_SHOWN = "replies.formShown"
    TOOLS_UNAVAILABLE = "replies.toolsUnavailable"
    # A receipt attached in the web panel (application/receipt_turn.py): the reply, and the note it pre-fills
    RECEIPT_READ = "replies.receiptRead"
    RECEIPT_NOTHING_FOUND = "replies.receiptNothingFound"
    RECEIPT_ITEMS = "receipt.items"
    RECEIPT_TAX = "receipt.tax"
    STALE_APPROVAL = "replies.staleApproval"
    CANCELLED = "replies.cancelled"
    CHANGED_SINCE = "replies.changedSince"
    DELETED = "replies.deleted"
    DELETE_FAILED = "replies.deleteFailed"
    # Errors a person is shown
    RUN_FAILED = "errors.runFailed"
    SERVICE_FAILED = "errors.serviceFailed"
    EMPTY_ANSWER = "errors.emptyAnswer"
    WRONG_SHAPE = "errors.wrongShape"
    TOOLS_UNREACHABLE = "errors.toolsUnreachable"
    NO_USER_MESSAGE = "errors.noUserMessage"
    MESSAGE_LENGTH = "errors.messageLength"
    INVALID_ACTION = "errors.invalidAction"
    ONE_RECEIPT = "errors.oneReceipt"
    INVALID_ATTACHMENT = "errors.invalidAttachment"
    RECEIPT_UNREADABLE = "errors.receiptUnreadable"
    RECEIPT_AGENT_UNAVAILABLE = "errors.receiptAgentUnavailable"
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
    # {month} is "November 2026"; {share} a percentage with one decimal ("84.9").
    ChatText.REPORT_TITLE: "Monthly report: {month}",
    ChatText.REPORT_DAILY_AVERAGE: "Daily average",
    ChatText.REPORT_OVER_DAYS: Plural(one="over {count} day", other="over {count} days"),
    ChatText.REPORT_CATEGORY_DETAILS: Plural(one="{share}% · {count} expense", other="{share}% · {count} expenses"),
    ChatText.REPORT_BIGGEST: "Biggest expense: {merchant}, {amount} on {date}",
    ChatText.REPORT_DOWNLOAD_CSV: "Download CSV",
    ChatText.REPORT_DOWNLOAD_MARKDOWN: "Download report (.md)",
    # {month} is "November 2026"; amounts are formatted money; {percent} has one decimal ("84.0").
    ChatText.BUDGETS_TITLE: "Budgets for {month}",
    ChatText.BUDGETS_NONE: "No budgets yet. Ask me to set one, or open Budgets.",
    ChatText.BUDGET_OVERALL: "Overall",
    ChatText.BUDGET_NO_OVERALL: "No overall limit",
    ChatText.BUDGET_SPENT_OF: "{spent} of {limit}",
    ChatText.BUDGET_USED: "{percent}% used · {state}",
    ChatText.BUDGET_OVER_BY: "Over by {amount}",
    ChatText.BUDGET_ELAPSED: "{percent}% of the month has gone by",
    ChatText.BUDGET_STATE_ON_TRACK: "on track",
    ChatText.BUDGET_STATE_NEAR_LIMIT: "near the limit",
    ChatText.BUDGET_STATE_OVER_LIMIT: "over the limit",
    # Under a saved expense: {name} is a category's name, or "Overall".
    ChatText.BUDGET_ALERT_NEAR: "{name} budget: {percent}% used ({spent} of {limit})",
    ChatText.BUDGET_ALERT_OVER: "{name} budget: over the limit ({spent} of {limit})",
    ChatText.LIST_NONE: "No matching expenses",
    ChatText.LIST_FOUND: Plural(one="Found {count} expense", other="Found {count} expenses"),
    ChatText.LIST_ROW_DETAILS: "{ref} · {category} · {date}",
    ChatText.LIST_MORE: "Showing the newest {shown} of {total}",
    ChatText.FORM_TITLE: "Add an expense",
    ChatText.FORM_AMOUNT: "Amount",
    ChatText.FORM_CURRENCY: "Currency (e.g. INR)",
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
    ChatText.TOO_MANY_STEPS: (
        "Sorry, that took too many steps, so I stopped. Could you try a simpler or more specific request?"
    ),
    ChatText.FORM_SHOWN: "Please check the details in the form and press Save.",
    ChatText.RECEIPT_READ: "I read the receipt. Check the details, fill in anything missing, and press Save.",
    ChatText.RECEIPT_NOTHING_FOUND: (
        "I couldn't find an expense on that file. Fill in the form yourself, or try a clearer photo."
    ),
    # The note a receipt pre-fills: its line items as printed ({items}), then its tax ({tax}, as printed).
    ChatText.RECEIPT_ITEMS: "Items: {items}.",
    ChatText.RECEIPT_TAX: "Tax: {tax}.",
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
    # The tool's own message (why the delete failed) goes to the server log only (D180).
    ChatText.DELETE_FAILED: "I couldn't delete {ref} just now. Nothing was deleted; ask me again in a moment.",
    # All a person is told about a bug in a run: the details go to the server log only.
    ChatText.RUN_FAILED: "Something went wrong on the server. The server log has the details.",
    # The model (or another outside service) failed; its own words go to the server log only (D180).
    ChatText.SERVICE_FAILED: "The assistant's service didn't answer properly. Try again in a moment.",
    ChatText.EMPTY_ANSWER: "The assistant didn't come up with an answer. Try asking again.",
    # Pydantic's explanation of the mismatch goes to the server log (at DEBUG: it quotes the answer).
    ChatText.WRONG_SHAPE: "The assistant's answer came back in a form the app can't use. Try again.",
    # Which server (its URL) goes to the server log only.
    ChatText.TOOLS_UNREACHABLE: "The expense tools can't be reached right now. Try again in a moment.",
    ChatText.NO_USER_MESSAGE: "The run has no user message to answer.",
    ChatText.MESSAGE_LENGTH: "The message must be 1 to {max} characters long.",
    ChatText.INVALID_ACTION: "The button's action isn't valid.",
    ChatText.ONE_RECEIPT: "Attach one receipt at a time.",
    # An attachment that isn't an uploaded receipt (sent inline or by URL, from another service, a bad id).
    ChatText.INVALID_ATTACHMENT: "The attachment isn't a receipt uploaded to this app. Upload it first.",
    # The receipt agent ran but couldn't read it (or answered something unusable); why goes to the server log (D180).
    ChatText.RECEIPT_UNREADABLE: "The receipt couldn't be read. Try again, or upload a clearer photo.",
    # The receipt agent isn't configured, can't be reached or refused us; why goes to the server log (D180).
    ChatText.RECEIPT_AGENT_UNAVAILABLE: (
        "The receipt reader isn't available right now. Try again in a moment, or fill in the expense yourself."
    ),
    ChatText.THREAD_ID_LENGTH: "threadId must be 1 to {max} characters long.",
    ChatText.FORM_TOO_LONG: "The form's values must be under {max} characters in total.",
}
