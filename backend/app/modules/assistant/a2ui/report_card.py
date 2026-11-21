"""The monthly report card: the month's total against the month before, the daily average, each category's part, the
biggest expense, and the Download CSV and Download report (.md) buttons (D209).

Presentation layer. cards.card_for draws it, in the request's language, for a successful get_monthly_report result
(the reports module's MonthlyReport, worked out by the monthly-report skill's script). Every value shown comes from
that result and is placed in a Text or a Stat: data to show, never instructions or markup.

The buttons don't send anything to the agent: each one calls the insights catalog's downloadReport function, which
the browser runs itself on a click (models.ClientFunction), with only the month and the format. The browser builds
the address and fetches the file as the signed-in person, so the card carries no URL and no data to download.
"""

from functools import partial

from app.core.i18n import Language, format_day, format_month, text
from app.core.money import format_money
from app.core.months import YearMonth
from app.modules import reports
from app.modules.assistant.a2ui.models import (
    ROOT_ID,
    Action,
    Button,
    Card,
    ClientFunction,
    Column,
    Component,
    CreateSurfaceMessage,
    DownloadReportArgs,
    FunctionCall,
    List,
    Row,
    Stat,
    Text,
)
from app.modules.assistant.a2ui.parts import new_surface_id, surface
from app.modules.assistant.a2ui.summary_card import versus
from app.modules.assistant.i18n import ChatText

# The download buttons, in the order shown: the spreadsheet first (primary), then the markdown report.
_DOWNLOADS = (
    (reports.ReportFormat.CSV, ChatText.REPORT_DOWNLOAD_CSV),
    (reports.ReportFormat.MARKDOWN, ChatText.REPORT_DOWNLOAD_MARKDOWN),
)


def _download_buttons(month: str, language: Language) -> list[Component]:
    """A row of buttons, each running downloadReport for `month` in its format when clicked."""
    components: list[Component] = [Row(id="downloads", children=[f"download_{form.value}" for form, _ in _DOWNLOADS])]
    for index, (form, label) in enumerate(_DOWNLOADS):
        call = FunctionCall(call=ClientFunction.DOWNLOAD_REPORT, args=DownloadReportArgs(month=month, format=form))
        button_id = f"download_{form.value}"
        components += [
            Button(
                id=button_id,
                child=f"{button_id}_label",
                action=Action(function_call=call),
                variant="primary" if index == 0 else None,
            ),
            Text(id=f"{button_id}_label", text=text(language, label)),
        ]
    return components


def _categories(report: reports.MonthlyReport, language: Language) -> list[Component]:
    """Each category's line: its name, its share and count, and its total (biggest first)."""
    t = partial(text, language)  # t(key, **values): a text in the request's language
    components: list[Component] = [List(id="categories", children=[f"cat_{i}" for i in range(len(report.by_category))])]
    for i, line in enumerate(report.by_category):
        details = t(ChatText.REPORT_CATEGORY_DETAILS, share=line.share_percent or 0, count=line.count)
        components += [
            Row(id=f"cat_{i}", children=[f"cat_{i}_info", f"cat_{i}_amount"], justify="spaceBetween"),
            Column(id=f"cat_{i}_info", children=[f"cat_{i}_name", f"cat_{i}_details"]),
            Text(id=f"cat_{i}_name", text=line.category),
            Text(id=f"cat_{i}_details", text=details, variant="caption"),
            Text(id=f"cat_{i}_amount", text=format_money(line.total, report.currency, language)),
        ]
    return components


def report_card(report: reports.MonthlyReport, language: Language) -> CreateSurfaceMessage:
    """The month's report as a card, in `language`; a month without expenses shows its total and no downloads."""
    t = partial(text, language)  # t(key, **values): a text in the request's language
    month = YearMonth.parse(report.month)
    month_and_year = format_month(month.first_day(), language)
    money = partial(format_money, currency=report.currency, language=language)
    change, trend = versus(report.total, report.previous_total, month.shift(-1).first_day(), language)
    spent_in = t(ChatText.SUMMARY_SPENT_IN, month=format_month(month.first_day(), language, with_year=False))
    components: list[Component] = [
        Text(id="title", text=t(ChatText.REPORT_TITLE, month=month_and_year), variant="caption"),
        Stat(id="stat_total", label=spent_in, value=money(report.total), change=change, trend=trend),
    ]
    body = ["title", "stats"]
    if not report.expense_count:
        components.append(Row(id="stats", children=["stat_total"]))
        no_expenses = t(ChatText.SUMMARY_NO_EXPENSES, month=month_and_year)
        components.append(Text(id="footer", text=no_expenses, variant="caption"))
        body.append("footer")
    else:
        over_days = t(ChatText.REPORT_OVER_DAYS, count=report.days_counted)
        label, value = t(ChatText.REPORT_DAILY_AVERAGE), money(report.daily_average)
        average = Stat(id="stat_average", label=label, value=value, change=over_days)
        components += [Row(id="stats", children=["stat_total", "stat_average"]), average]
        components += _categories(report, language)
        body.append("categories")
        if report.biggest:
            top = report.biggest[0]
            biggest = t(
                ChatText.REPORT_BIGGEST,
                merchant=top.merchant,
                amount=money(top.amount),
                date=format_day(top.spent_on, language),
            )
            components.append(Text(id="biggest", text=biggest, variant="caption"))
            body.append("biggest")
        components += _download_buttons(report.month, language)
        body.append("downloads")
    components += [Card(id=ROOT_ID, child="body"), Column(id="body", children=body)]
    return surface(new_surface_id("report"), components)
