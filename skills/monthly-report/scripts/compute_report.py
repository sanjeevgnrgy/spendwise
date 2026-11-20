"""Computes a monthly report's figures: the monthly-report skill's script (D209).

Reads one JSON object on standard input and writes one on standard output, so it can be run on its own:

    python scripts/compute_report.py < input.json

Input:  {"month": "2026-11", "today": "2026-11-20",
         "expenses": [{"spent_on": "2026-11-03", "amount": "450.50", "category": "Food", "merchant": "Swiggy",
                       "payment_method": "upi"}, ...]}
        (the expenses of the month and of the month before, amounts in INR as decimal strings)
Output: the figures (amounts as decimal strings, rounded half up to paise): total, previous_total, change_percent,
        expense_count, daily_average (over the days so far, for the running month), by_category (with each one's
        share), by_payment_method, and the five biggest expenses.

The backend runs it in a separate process, with a time limit, on the signed-in person's own expenses; the model never
runs it and never sees its code. Standard library only; no files, no network.
"""

import calendar
import json
import sys
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")
ONE_DECIMAL = Decimal("0.1")
BIGGEST = 5
CURRENCY = "INR"


def money(value: Decimal) -> str:
    """A decimal amount as a string with two decimals ("1250.50")."""
    return str(value.quantize(CENTS, rounding=ROUND_HALF_UP))


def percent(part: Decimal, whole: Decimal) -> str | None:
    """`part` as a percentage of `whole`, one decimal; None when there is no whole to compare with."""
    return None if whole == 0 else str((part * 100 / whole).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP))


def month_of(day: str) -> str:
    """The YYYY-MM a YYYY-MM-DD date falls in."""
    return day[:7]


def previous_month(month: str) -> str:
    """The month before a YYYY-MM month."""
    year, number = int(month[:4]), int(month[5:7])
    return f"{year - 1}-12" if number == 1 else f"{year}-{number - 1:02d}"


def totals(rows: list[dict], key: str) -> list[dict]:
    """Each value of `key` with its total, count and share of the whole, biggest first."""
    sums: dict[str, Decimal] = defaultdict(Decimal)
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        sums[row[key]] += Decimal(row["amount"])
        counts[row[key]] += 1
    whole = sum(sums.values(), Decimal(0))
    ranked = sorted(sums.items(), key=lambda item: (-item[1], item[0]))
    return [{key: name, "total": money(amount), "count": counts[name], "share_percent": percent(amount, whole)}
            for name, amount in ranked]


def compute(data: dict) -> dict:
    """The report's figures for data["month"], from data["expenses"] (that month's and the month before's)."""
    month, today = data["month"], date.fromisoformat(data["today"])
    rows = [row for row in data["expenses"] if month_of(row["spent_on"]) == month]
    before = [row for row in data["expenses"] if month_of(row["spent_on"]) == previous_month(month)]
    total = sum((Decimal(row["amount"]) for row in rows), Decimal(0))
    previous = sum((Decimal(row["amount"]) for row in before), Decimal(0))
    year, number = int(month[:4]), int(month[5:7])
    days_in_month = calendar.monthrange(year, number)[1]
    # The running month is averaged over the days so far; a past month over all its days.
    days = today.day if (today.year, today.month) == (year, number) else days_in_month
    biggest = sorted(rows, key=lambda row: (-Decimal(row["amount"]), row["spent_on"]))[:BIGGEST]
    return {
        "month": month,
        "currency": CURRENCY,
        "total": money(total),
        "previous_total": money(previous),
        "change_percent": percent(total - previous, previous),
        "expense_count": len(rows),
        "days_counted": days,
        "daily_average": money(total / days),
        "by_category": totals(rows, "category"),
        "by_payment_method": totals(rows, "payment_method"),
        "biggest": [{key: row[key] for key in ("spent_on", "merchant", "category", "amount")} for row in biggest],
    }


if __name__ == "__main__":
    json.dump(compute(json.load(sys.stdin)), sys.stdout)
