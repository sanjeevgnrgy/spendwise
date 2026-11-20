"""Reports module: a person's monthly report, worked out by the monthly-report Agent Skill's script (D209).

This file is the module's public interface. Other modules import ONLY the contract names below, from
`app.modules.reports`. The use case, the documents and the router stay private; the composition root plugs them in
through module.py.

The figures come from skills/monthly-report/scripts/compute_report.py, which the server runs (never the model) on the
signed-in person's own expenses, read through the expenses and categories modules' queries; its answer is checked
(MonthlyReport) before anyone sees it. The downloads (CSV and markdown) are written in the person's language.

Depends on: expenses, categories. Who uses it: the MCP server (MonthlyReports and MonthlyReport for its
get_monthly_report tool), the assistant (MonthlyReport and ReportFormat for the report card) and the web contract
(ReportFormat).
"""

from app.modules.reports.application.monthly_reports import MonthlyReports, ReportFile
from app.modules.reports.models import BigExpense, CategoryShare, MonthlyReport, PaymentShare
from app.modules.reports.values import ReportFormat

__all__ = [
    "BigExpense",
    "CategoryShare",
    "MonthlyReport",
    "MonthlyReports",
    "PaymentShare",
    "ReportFile",
    "ReportFormat",
]
