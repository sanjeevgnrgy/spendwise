"""Every expense of a month as CSV, in the person's language: the "Download CSV" file.

Part of the reports module (documents/): a pure function of the month's expenses, used by the use case
(application/monthly_reports.py). RFC 4180 CSV (Python's csv module, CRLF line ends), behind a UTF-8 byte order mark so
spreadsheet programs read Hindi and the ₹ sign correctly. The column names come from the module's catalog; amounts are
plain decimals ("1250.50") and dates ISO ("2026-11-03"), so a spreadsheet reads them as numbers and dates.

A cell that starts with "=", "+", "-", "@" (or their full-width forms), a tab, a carriage return or a line feed can be
a formula to a spreadsheet program, so text from the person's data (merchant, category, note) that starts with one
gets a leading apostrophe: it's shown as text, never run (OWASP's CSV injection advice, sources.md section 35).
"""

import csv
import io

from app.core.i18n import Language, text
from app.core.money import paise_to_rupees
from app.modules import categories, expenses
from app.modules.reports.i18n import ReportText

BYTE_ORDER_MARK = "﻿"
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠")
COLUMNS = (
    ReportText.COLUMN_DATE,
    ReportText.COLUMN_MERCHANT,
    ReportText.COLUMN_CATEGORY,
    ReportText.COLUMN_PAYMENT_METHOD,
    ReportText.COLUMN_AMOUNT,
    ReportText.COLUMN_CURRENCY,
    ReportText.COLUMN_AMOUNT_INR,
    ReportText.COLUMN_NOTE,
)


def _as_text(value: str) -> str:
    """Person-written text that a spreadsheet will show as text, never evaluate as a formula."""
    return f"'{value}" if value.startswith(FORMULA_STARTS) else value


def expenses_csv(rows: list[expenses.ExpenseRead], names: dict[int, str], language: Language) -> str:
    """The expenses as CSV, oldest first, with a header line in `language`. `names` gives each category's name by id
    (a category that no longer exists is categories.UNKNOWN_CATEGORY). The INR amount is empty for an expense in
    another currency saved before it could be converted."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([text(language, column) for column in COLUMNS])
    for row in sorted(rows, key=lambda expense: (expense.spent_on, expense.id)):
        inr = "" if row.base_amount_minor is None else str(paise_to_rupees(row.base_amount_minor))
        writer.writerow(
            [
                row.spent_on.isoformat(),
                _as_text(row.merchant),
                _as_text(names.get(row.category_id, categories.UNKNOWN_CATEGORY)),
                expenses.payment_method_label(row.payment_method, language),
                str(row.amount),
                row.currency,
                inr,
                _as_text(row.note or ""),
            ]
        )
    return BYTE_ORDER_MARK + out.getvalue()
