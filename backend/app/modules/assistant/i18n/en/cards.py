"""The assistant's texts in English: the cards (a2ui/) and the expense form (a2ui/forms.py).

Part of the assistant module (i18n/): the source every other language translates. The keys are in keys.py.
"""

from app.core.i18n import Plural, TextValue
from app.modules.assistant.i18n.keys import ChatText

CARDS: dict[ChatText, TextValue] = {
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
}
