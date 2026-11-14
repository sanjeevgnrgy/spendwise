"""The month's summary card: what was spent against the month before, the biggest category, and a donut chart.

Presentation layer. cards.card_for draws it, in the request's language, for a successful get_summary result (the
MCP server's MonthSpending). Every value shown comes from that result and is placed in a Text, a Stat or a chart
point: data to show, never instructions or markup.
"""

from datetime import date
from decimal import Decimal
from functools import partial

from app.core.i18n import Language, format_month, text
from app.core.money import CURRENCY_SYMBOLS, format_money
from app.core.months import YearMonth
from app.modules.assistant.a2ui.models import (
    ROOT_ID,
    Card,
    Chart,
    ChartPoint,
    ChartType,
    Column,
    Component,
    CreateSurfaceMessage,
    Row,
    Stat,
    Text,
    Trend,
)
from app.modules.assistant.a2ui.parts import new_surface_id, surface
from app.modules.assistant.i18n import ChatText
from app.modules.mcp import MonthSpending

# A donut reads best with a few slices, and the theme has five chart colours: the top four
# categories, then everything else together.
DONUT_SLICES = 4


def _versus(total: Decimal, previous: Decimal, previous_month: date, language: Language) -> tuple[str, Trend]:
    """'+12% vs October', and which way it went."""
    name = format_month(previous_month, language, with_year=False)
    if previous == 0:
        return text(language, ChatText.SUMMARY_NOTHING_BEFORE, month=name), Trend.FLAT
    if total == previous:
        return text(language, ChatText.SUMMARY_SAME_AS, month=name), Trend.FLAT
    change = (total - previous) / previous * 100
    # Small changes keep a decimal, so ₹10,040 vs ₹10,000 reads "+0.4%", not "Same as".
    percent = f"{change:+.1f}%" if abs(change) < 1 else f"{round(change):+d}%"
    trend = Trend.UP if change > 0 else Trend.DOWN
    return text(language, ChatText.SUMMARY_CHANGE, change=percent, month=name), trend


def _categories(summary: MonthSpending, language: Language) -> list[Component]:
    """The biggest category as a Stat (its total, and its share of the month's), then the donut of the categories.

    Only for a month with spending: `summary.by_category` isn't empty, and comes biggest first.
    """
    t = partial(text, language)  # t(key, **values): a text in the request's language
    top = summary.by_category[0]
    share = round(top.total / summary.total * 100) if summary.total else 0
    amount = format_money(top.total, summary.currency, language)
    slices = [ChartPoint(label=c.category_name, value=float(c.total)) for c in summary.by_category[:DONUT_SLICES]]
    rest = sum((c.total for c in summary.by_category[DONUT_SLICES:]), Decimal(0))
    if rest:
        slices.append(ChartPoint(label=t(ChatText.SUMMARY_EVERYTHING_ELSE), value=float(rest)))
    return [
        Stat(
            id="stat_top",
            label=t(ChatText.SUMMARY_TOP_CATEGORY),
            value=top.category_name,
            change=t(ChatText.SUMMARY_TOP_SHARE, amount=amount, share=share),
        ),
        Chart(id="chart", chart_type=ChartType.DONUT, data=slices, unit=CURRENCY_SYMBOLS.get(summary.currency)),
    ]


def summary_card(summary: MonthSpending, language: Language) -> CreateSurfaceMessage:
    """Where the money went in one month: two Stats (vs last month, biggest category) and a donut chart."""
    t = partial(text, language)  # t(key, **values): a text in the request's language
    month = YearMonth.parse(summary.month).first_day()
    previous_month = YearMonth.parse(summary.previous_month.month).first_day()
    change, trend = _versus(summary.total, summary.previous_month.total, previous_month, language)
    month_and_year = format_month(month, language)
    components: list[Component] = [
        Text(id="title", text=t(ChatText.SUMMARY_TITLE, month=month_and_year), variant="caption"),
        Stat(
            id="stat_total",
            label=t(ChatText.SUMMARY_SPENT_IN, month=format_month(month, language, with_year=False)),
            value=format_money(summary.total, summary.currency, language),
            change=change,
            trend=trend,
        ),
    ]
    spent = bool(summary.by_category)
    if spent:
        components += _categories(summary, language)
    count = summary.expense_count
    if count:
        footer = t(ChatText.SUMMARY_EXPENSE_COUNT, count=count)
    else:
        footer = t(ChatText.SUMMARY_NO_EXPENSES, month=month_and_year)
    components.append(Text(id="footer", text=footer, variant="caption"))
    stats = ["stat_total"] + (["stat_top"] if spent else [])
    body = ["title", "stats"] + (["chart"] if spent else []) + ["footer"]
    components += [Card(id=ROOT_ID, child="body"), Column(id="body", children=body), Row(id="stats", children=stats)]
    return surface(new_surface_id("summary"), components)
