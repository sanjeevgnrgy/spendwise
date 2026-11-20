"""The reports module's texts for people, in English: their keys, and the source every other language translates.

Part of the reports module (i18n/). The errors of making a report (a problem's detail), the markdown report's headings
and sentences (documents/markdown.py) and the CSV's column names (documents/spreadsheet.py). hi.py translates them;
__init__.py registers the catalog. Amounts, months and days are written by core.i18n's formatters, not here.
"""

from enum import StrEnum

from app.core.i18n import Plural, TextValue


class ReportText(StrEnum):
    """The reports module's texts, by key."""

    UNAVAILABLE = "errors.unavailable"
    TOO_MANY_EXPENSES = "errors.tooManyExpenses"
    TITLE = "markdown.title"
    TOTAL = "markdown.total"
    NOTHING_SPENT = "markdown.nothingSpent"
    COMPARED_HEADING = "markdown.comparedHeading"
    COMPARED_UP = "markdown.comparedUp"
    COMPARED_DOWN = "markdown.comparedDown"
    COMPARED_SAME = "markdown.comparedSame"
    COMPARED_NONE = "markdown.comparedNone"
    CATEGORIES_HEADING = "markdown.categoriesHeading"
    PAYMENTS_HEADING = "markdown.paymentsHeading"
    BIGGEST_HEADING = "markdown.biggestHeading"
    AVERAGE_HEADING = "markdown.averageHeading"
    AVERAGE = "markdown.average"
    IN_INR = "markdown.inInr"
    COLUMN_DATE = "columns.date"
    COLUMN_MERCHANT = "columns.merchant"
    COLUMN_CATEGORY = "columns.category"
    COLUMN_PAYMENT_METHOD = "columns.paymentMethod"
    COLUMN_AMOUNT = "columns.amount"
    COLUMN_CURRENCY = "columns.currency"
    COLUMN_AMOUNT_INR = "columns.amountInInr"
    COLUMN_NOTE = "columns.note"
    COLUMN_SHARE = "columns.share"
    COLUMN_COUNT = "columns.count"


EN: dict[ReportText, TextValue] = {
    # The skill's script failed or answered something unusable; why goes to the server log (D180).
    ReportText.UNAVAILABLE: "The report couldn't be made right now. Try again in a moment.",
    ReportText.TOO_MANY_EXPENSES: "This month has too many expenses for a report (more than {limit}).",
    # Markdown: {month} is "November 2026" (format_month); amounts are formatted money ("₹4,300.50").
    ReportText.TITLE: "SpendWise report: {month}",
    ReportText.TOTAL: Plural(one="{total} spent, in {count} expense.", other="{total} spent, in {count} expenses."),
    ReportText.NOTHING_SPENT: "No expenses were recorded this month.",
    ReportText.COMPARED_HEADING: "Compared with {previous_month}",
    # {percent} is the change's size, without a sign ("12.5").
    ReportText.COMPARED_UP: "Up {percent}% on {previous_month}, when {previous_total} was spent.",
    ReportText.COMPARED_DOWN: "Down {percent}% on {previous_month}, when {previous_total} was spent.",
    ReportText.COMPARED_SAME: "The same as {previous_month}: {previous_total}.",
    ReportText.COMPARED_NONE: "Nothing was recorded in {previous_month}, so there's nothing to compare with.",
    ReportText.CATEGORIES_HEADING: "By category",
    ReportText.PAYMENTS_HEADING: "By payment method",
    ReportText.BIGGEST_HEADING: "Biggest expenses",
    ReportText.AVERAGE_HEADING: "Daily average",
    ReportText.AVERAGE: Plural(one="{average} a day, over {count} day.", other="{average} a day, over {count} days."),
    ReportText.IN_INR: "Amounts are in Indian rupees: an expense in another currency counts at its amount in INR.",
    # Column names: the markdown report's tables and the CSV's first line.
    ReportText.COLUMN_DATE: "Date",
    ReportText.COLUMN_MERCHANT: "Merchant",
    ReportText.COLUMN_CATEGORY: "Category",
    ReportText.COLUMN_PAYMENT_METHOD: "Payment method",
    ReportText.COLUMN_AMOUNT: "Amount",
    ReportText.COLUMN_CURRENCY: "Currency",
    ReportText.COLUMN_AMOUNT_INR: "Amount in INR",
    ReportText.COLUMN_NOTE: "Note",
    ReportText.COLUMN_SHARE: "Share",
    ReportText.COLUMN_COUNT: "Expenses",
}
