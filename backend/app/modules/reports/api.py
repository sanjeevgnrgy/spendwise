"""HTTP routes for reports: they only translate HTTP into the MonthlyReports use case.

The reports module's REST adapter. module.create_router builds the router with the use case passed in, and the
composition root mounts it under /api/v1, behind the session and X-CSRF checks. The web app's report card (the
assistant's A2UI "downloadReport" function) downloads from the second route. Every route acts for the signed-in
person (D190). A route's docstring would become its OpenAPI text, so notes are `#` comments.

Plain `def` routes: running the skill's script blocks, so FastAPI runs them in a worker thread and other requests
aren't held up.
"""

from typing import Annotated

from fastapi import APIRouter, Path, Response

from app.core.months import YearMonth
from app.modules.reports.application.monthly_reports import MonthlyReports
from app.modules.reports.models import MonthlyReport
from app.modules.reports.values import MEDIA_TYPES, ReportFormat
from app.web.auth import CurrentUserDep
from app.web.dependencies import LanguageDep

TAG = "reports"
MonthPath = Annotated[str, Path(pattern=YearMonth.PATTERN, examples=["2026-11"])]
# What the download route answers with, for the OpenAPI document: text, as CSV or markdown.
_FILE_CONTENT = {
    "content": {media_type.split(";")[0]: {"schema": {"type": "string"}} for media_type in MEDIA_TYPES.values()}
}


def create_router(reports: MonthlyReports) -> APIRouter:
    """The routes, with the use case handed in (constructor injection)."""
    router = APIRouter(tags=[TAG])

    # GET /api/v1/reports/monthly/{month}: the month's figures (the monthly-report skill's script works them out, in
    # INR): the total against the month before, by category, by payment method, the biggest expenses, the daily
    # average. 502 if the report can't be made right now.
    @router.get("/reports/monthly/{month}")
    def get_monthly_report(month: MonthPath, principal: CurrentUserDep) -> MonthlyReport:
        return reports.figures(principal.user_id, YearMonth.parse(month))

    # GET /api/v1/reports/monthly/{month}/{format}: the month's report as a file to save, in the request's language:
    # "csv" (every expense of the month) or "md" (the report in markdown). Sent as an attachment, with its name.
    @router.get("/reports/monthly/{month}/{format}", response_class=Response, responses={200: _FILE_CONTENT})
    def download_monthly_report(
        month: MonthPath, format: ReportFormat, principal: CurrentUserDep, language: LanguageDep
    ) -> Response:
        file = reports.download(principal.user_id, YearMonth.parse(month), format, language)
        disposition = f'attachment; filename="{file.name}"'
        return Response(file.content, media_type=file.media_type, headers={"Content-Disposition": disposition})

    return router
