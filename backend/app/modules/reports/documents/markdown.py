"""The monthly report written out as markdown, in the person's language: the "Download report (.md)" file.

Part of the reports module (documents/): a pure function of the checked figures (models.MonthlyReport), used by
the use case (application/monthly_reports.py). The sections and their order are the ones the monthly-report skill
describes (skills/monthly-report/SKILL.md). Every text comes from the module's catalog; amounts, months and days
from core.i18n's formatters. Names from the person's data (merchants, categories) are escaped, so they're shown as
written and can't become a link, an image, HTML or a broken table.
"""

import re
from collections.abc import Callable, Iterable
from datetime import date
from decimal import Decimal
from functools import partial

from app.core.i18n import Language, format_day, format_month, text
from app.core.money import format_money
from app.core.months import YearMonth
from app.modules import expenses
from app.modules.reports.i18n import ReportText
from app.modules.reports.models import MonthlyReport

# The characters that mean something in markdown (emphasis, code, links, images, HTML, headings, tables).
_MARKUP = re.compile(r"([\\`*_\[\]<>|#~!])")


def _escaped(value: str) -> str:
    """Person-written text as one line of literal markdown: whitespace runs (newlines too) become one space, and
    markup characters are escaped."""
    return _MARKUP.sub(r"\\\1", " ".join(value.split()))


def _table(headers: Iterable[str], rows: Iterable[Iterable[str]], numeric_from: int) -> list[str]:
    """A markdown table; the columns from `numeric_from` on are right-aligned (they hold numbers)."""
    headers = list(headers)
    rule = ["---" if i < numeric_from else "---:" for i in range(len(headers))]
    return ["| " + " | ".join(line) + " |" for line in [headers, rule, *rows]]


def _percent(value: Decimal | None) -> str:
    """A share as "84.9%", or an empty cell when there's none."""
    return "" if value is None else f"{value}%"


def _comparison(report: MonthlyReport, language: Language, previous: date) -> str:
    """How the month compares with the one before: up, down, the same, or nothing to compare with."""
    values = {
        "previous_month": format_month(previous, language),
        "previous_total": format_money(report.previous_total, report.currency, language),
    }
    change = report.change_percent
    if change is None:
        return text(language, ReportText.COMPARED_NONE, **values)
    key = ReportText.COMPARED_UP if change > 0 else ReportText.COMPARED_DOWN if change < 0 else ReportText.COMPARED_SAME
    return text(language, key, percent=abs(change), **values)


def _breakdowns(report: MonthlyReport, language: Language, money: Callable[[Decimal], str]) -> list[str]:
    """The sections of a month that had expenses: by category, by payment method, the biggest, the daily average."""
    t = partial(text, language)  # t(key, **values): a text in `language`
    numbers = [t(ReportText.COLUMN_AMOUNT), t(ReportText.COLUMN_SHARE), t(ReportText.COLUMN_COUNT)]
    by_category = [
        [_escaped(line.category), money(line.total), _percent(line.share_percent), str(line.count)]
        for line in report.by_category
    ]
    by_payment = [
        [
            expenses.payment_method_label(line.payment_method, language),
            money(line.total),
            _percent(line.share_percent),
            str(line.count),
        ]
        for line in report.by_payment_method
    ]
    biggest = [
        [format_day(line.spent_on, language), _escaped(line.merchant), _escaped(line.category), money(line.amount)]
        for line in report.biggest
    ]
    biggest_headers = [t(ReportText.COLUMN_DATE), t(ReportText.COLUMN_MERCHANT), t(ReportText.COLUMN_CATEGORY)]
    average = t(ReportText.AVERAGE, average=money(report.daily_average), count=report.days_counted)
    return [
        f"## {t(ReportText.CATEGORIES_HEADING)}",
        "",
        *_table([t(ReportText.COLUMN_CATEGORY), *numbers], by_category, numeric_from=1),
        "",
        f"## {t(ReportText.PAYMENTS_HEADING)}",
        "",
        *_table([t(ReportText.COLUMN_PAYMENT_METHOD), *numbers], by_payment, numeric_from=1),
        "",
        f"## {t(ReportText.BIGGEST_HEADING)}",
        "",
        *_table([*biggest_headers, t(ReportText.COLUMN_AMOUNT)], biggest, numeric_from=3),
        "",
        f"## {t(ReportText.AVERAGE_HEADING)}",
        "",
        average,
        "",
    ]


def report_markdown(report: MonthlyReport, language: Language) -> str:
    """The report as a markdown document, in `language`: the month's total, the comparison with the month before, then
    (for a month with expenses) the spending by category and by payment method, the biggest expenses and the daily
    average, and a closing note that amounts are in INR."""
    t = partial(text, language)  # t(key, **values): a text in `language`
    money: Callable[[Decimal], str] = partial(format_money, currency=report.currency, language=language)
    month = YearMonth.parse(report.month)
    previous = month.shift(-1).first_day()
    title = t(ReportText.TITLE, month=format_month(month.first_day(), language))
    if report.expense_count == 0:
        total = t(ReportText.NOTHING_SPENT)
    else:
        total = t(ReportText.TOTAL, total=money(report.total), count=report.expense_count)
    lines = [
        f"# {title}",
        "",
        total,
        "",
        f"## {t(ReportText.COMPARED_HEADING, previous_month=format_month(previous, language))}",
        "",
        _comparison(report, language, previous),
        "",
    ]
    if report.expense_count:
        lines += _breakdowns(report, language, money)
    lines += [f"_{t(ReportText.IN_INR)}_", ""]
    return "\n".join(lines)
