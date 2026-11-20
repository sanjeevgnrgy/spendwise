"""MonthlyReports: a person's monthly report, worked out by the monthly-report skill's script (D209), and its downloads.

The reports module's use case (application/). Not a bus handler: running the script takes a moment, and a handler
runs inside a database session that would be held open meanwhile. So it reads the person's expenses through the
expenses and categories modules' queries (each its own short unit of work), then runs the script with no session
open, then checks the script's answer (models.MonthlyReport) before anyone sees it.

Built by module.create_reports with the bus, the skill library and the clock passed in. The routes (api.py) and the
MCP tool get_monthly_report (through the mcp module's ToolContext) use it.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from pydantic import ValidationError

from app.core.clock import Clock
from app.core.cqrs import MessageBus
from app.core.errors import BusinessRuleError, ExternalServiceError
from app.core.i18n import Language, translatable
from app.core.ids import UserId
from app.core.money import paise_to_rupees
from app.core.months import YearMonth
from app.core.skills import SkillLibrary, SkillNotFoundError, SkillScriptError
from app.modules import categories, expenses
from app.modules.reports.documents.markdown import report_markdown
from app.modules.reports.documents.spreadsheet import expenses_csv
from app.modules.reports.i18n import ReportText
from app.modules.reports.models import MonthlyReport
from app.modules.reports.values import (
    FILE_NAME_PREFIX,
    MAX_REPORT_EXPENSES,
    MEDIA_TYPES,
    REPORT_SCRIPT,
    REPORT_SKILL,
    ReportFormat,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReportFile:
    """A download: its file name, its media type and its text."""

    name: str
    media_type: str
    content: str


@dataclass(frozen=True)
class _Month:
    """What a report is made from: the expenses of the month and the month before (newest first), and category names
    by id."""

    rows: list[expenses.ExpenseRead]
    names: dict[int, str]


class MonthlyReports:
    """A person's monthly report: its figures, or one of its downloads."""

    def __init__(self, bus: MessageBus, skills: SkillLibrary, clock: Clock) -> None:
        self._bus = bus
        self._skills = skills
        self._clock = clock

    def figures(self, owner: UserId, month: YearMonth) -> MonthlyReport:
        """The month's figures for `owner`. Raises BusinessRuleError for a month with too many expenses to report on,
        ExternalServiceError (a text for people) when the script fails or answers something unusable."""
        return self._run_script(month, self._read(owner, month))

    def download(self, owner: UserId, month: YearMonth, form: ReportFormat, language: Language) -> ReportFile:
        """The month's report as a file, in `language`: the markdown report, or every expense of the month as CSV.
        Raises as figures() does."""
        data = self._read(owner, month)
        if form is ReportFormat.CSV:
            in_month = [row for row in data.rows if YearMonth.of(row.spent_on) == month]
            content = expenses_csv(in_month, data.names, language)
        else:
            content = report_markdown(self._run_script(month, data), language)
        return ReportFile(f"{FILE_NAME_PREFIX}-{month}.{form.value}", MEDIA_TYPES[form], content)

    def _read(self, owner: UserId, month: YearMonth) -> _Month:
        """Every expense of `owner`'s in the month and the month before, read a page at a time, and the category
        names. Only their own expenses are ever read (ListExpenses always names the owner, D190)."""
        start, end = month.shift(-1).first_day(), month.shift(1).first_day() - timedelta(days=1)
        rows: list[expenses.ExpenseRead] = []
        while True:
            filters = expenses.ExpenseFilters(
                start_date=start, end_date=end, limit=expenses.MAX_LIST_LIMIT, offset=len(rows)
            )
            page = self._bus.ask(expenses.ListExpenses(owner_id=owner, filters=filters))
            # A report on part of a month would be wrong without saying so: refuse instead.
            if page.total > MAX_REPORT_EXPENSES:
                raise BusinessRuleError(translatable(ReportText.TOO_MANY_EXPENSES, limit=MAX_REPORT_EXPENSES))
            rows += page.items
            if not page.items or len(rows) >= page.total:
                break
        names = {category.id: category.name for category in self._bus.ask(categories.ListCategories())}
        return _Month(rows, names)

    def _run_script(self, month: YearMonth, data: _Month) -> MonthlyReport:
        """Run the skill's script on the expenses that have an INR amount, and check its answer."""
        # Every currency counts through its INR amount (D204); one saved before it could be converted has none yet,
        # so it's left out, as in the monthly summary. No notes: the figures don't need them.
        payload = {
            "month": str(month),
            "today": self._clock.today().isoformat(),
            "expenses": [
                {
                    "spent_on": row.spent_on.isoformat(),
                    "amount": str(paise_to_rupees(row.base_amount_minor)),
                    "category": data.names.get(row.category_id, categories.UNKNOWN_CATEGORY),
                    "merchant": row.merchant,
                    "payment_method": row.payment_method.value,
                }
                for row in data.rows
                if row.base_amount_minor is not None
            ],
        }
        try:
            report = MonthlyReport.model_validate(self._skills.run_script(REPORT_SKILL, REPORT_SCRIPT, payload))
        except (SkillNotFoundError, SkillScriptError, ValidationError) as exc:
            # What went wrong goes to the log, at DEBUG (it may quote the person's data); people get a catalogued text.
            logger.warning("the monthly report for %s couldn't be made: %s", month, type(exc).__name__)
            logger.debug("monthly report failure: %s", exc)
            raise ExternalServiceError(translatable(ReportText.UNAVAILABLE)) from exc
        if report.month != str(month):
            logger.warning("the report script answered for %s, not %s", report.month, month)
            raise ExternalServiceError(translatable(ReportText.UNAVAILABLE))
        return report
