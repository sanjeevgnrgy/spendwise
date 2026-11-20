"""The reports module's shared values: which skill script works a report out, the download formats, and their limits.

Part of the module's contract layer. The use case (application/monthly_reports.py), the documents (documents/) and the
routes (api.py) use them; __init__.py exports what the MCP tool, the assistant's card and the web contract need. This
file imports no other file of the module.
"""

from enum import StrEnum

# The Agent Skill whose script works the figures out (skills/monthly-report, D209), and that script. The server runs
# it (core/skills.SkillLibrary.run_script); the model only reads the skill's instructions.
REPORT_SKILL = "monthly-report"
REPORT_SCRIPT = "scripts/compute_report.py"

# The script's answer is checked before anyone sees it: at most this many lines per breakdown (categories and payment
# methods are few; the cap stops a broken script flooding a card) and exactly this many biggest expenses at most.
MAX_BREAKDOWN_LINES = 50
MAX_BIGGEST = 5

# ListExpenses answers in pages; the report reads every page of the two months, at most this many expenses in all.
# A month past it is refused with a text for people rather than reported on part of its expenses.
MAX_REPORT_EXPENSES = 10_000


# The downloads: a spreadsheet of the month's expenses, or the report written out in markdown. The value is the last
# part of the route (GET /reports/monthly/{month}/{format}) and the file's extension; the web app's Download buttons
# name it through the generated contract.
class ReportFormat(StrEnum):
    CSV = "csv"
    MARKDOWN = "md"


# How each download is sent: its media type (UTF-8 text) and the start of its file name ("spendwise-2026-11.csv").
MEDIA_TYPES = {ReportFormat.CSV: "text/csv; charset=utf-8", ReportFormat.MARKDOWN: "text/markdown; charset=utf-8"}
FILE_NAME_PREFIX = "spendwise"
