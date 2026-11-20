---
name: monthly-report
description: Builds a person's monthly spending report (totals against the month before, categories, payment methods, the biggest expenses) and tells you how to present it. Use when the user asks for a monthly report, a month's statement or summary to keep, or a report they can download (CSV or markdown).
---

# The monthly report

## Steps

1. Work out the month (YYYY-MM). "This month" is today's month; "last month" the one before. If the user gave no
   month and it isn't clear, ask which one.
2. Call `get_monthly_report` with that month. The server works the figures out (`scripts/compute_report.py`, run on
   the user's own expenses) and shows them as a report card with "Download CSV" and "Download report (.md)" buttons.
   Never work the figures out yourself, and never repeat every number: the card shows them.
3. Reply in two or three short sentences, in the user's language, then stop.

## What the reply says

- **First:** the month's total, and how it compares with the month before (up or down, by how much, in percent if
  the tool gives it).
- **Then:** the biggest category and its share, and the single biggest expense if it stands out.
- **Last:** that the full report can be downloaded from the card as CSV or markdown.

## Tone

Plain, calm and factual, like a good bank statement with one friendly line. No judgement ("you overspent"), no
advice unless asked, no exclamation marks, no emojis. Amounts in rupees with the ₹ sign.

## What the report contains (the downloads)

The markdown report has these sections, in this order: the month and its total; compared with the month before;
spending by category (amount, share, number of expenses); by payment method; the five biggest expenses; the daily
average. The CSV lists every expense of the month, one per line. Both are written by the server, in the app's
language, from the same figures as the card.

## If something is off

- The month has no expenses: say so in one sentence, and don't call the tool again for the same month.
- The tool fails: say the report couldn't be made right now; don't make one up.
