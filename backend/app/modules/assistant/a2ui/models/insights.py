"""SpendWise's insights catalog: Chart and Stat. Data and labels only, no colours, sizes or code: how a chart
looks is the renderer's decision. They sit on basic-catalog surfaces and name their catalog with "@catalogId".

Part of the assistant's A2UI models (presentation layer). The classes are Pydantic models, so they're described in `#`
comments: a docstring would become part of their JSON schema.
"""

from typing import Literal

from pydantic import Field

from app.modules import categories
from app.modules.assistant.a2ui.models.base import (
    MAX_CHART_POINTS,
    MAX_STAT_TEXT_LENGTH,
    MAX_UNIT_LENGTH,
    A2uiModel,
    Catalog,
    ChartType,
    ComponentId,
    Trend,
)


# One bar, point or slice of a Chart.
class ChartPoint(A2uiModel):
    label: str = Field(max_length=categories.MAX_NAME_LENGTH)  # points are categories, so: as long as their names
    value: float = Field(allow_inf_nan=False)  # NaN or infinity isn't valid JSON, nor a sensible bar


# A chart from the insights catalog: data and a unit only; the renderer decides how it looks.
class Chart(A2uiModel):
    id: ComponentId
    component: Literal["Chart"] = "Chart"
    catalog_id: Literal[Catalog.INSIGHTS] = Field(default=Catalog.INSIGHTS, alias="@catalogId")
    chart_type: ChartType
    data: list[ChartPoint] = Field(min_length=1, max_length=MAX_CHART_POINTS)
    unit: str | None = Field(default=None, max_length=MAX_UNIT_LENGTH)  # shown before values, e.g. "₹"


class Stat(A2uiModel):
    """One number worth noticing: "Spent in November: ₹9,265.85, +12% vs October"."""

    id: ComponentId
    component: Literal["Stat"] = "Stat"
    catalog_id: Literal[Catalog.INSIGHTS] = Field(default=Catalog.INSIGHTS, alias="@catalogId")
    label: str = Field(max_length=MAX_STAT_TEXT_LENGTH)
    value: str = Field(max_length=MAX_STAT_TEXT_LENGTH)
    change: str | None = Field(default=None, max_length=MAX_STAT_TEXT_LENGTH)
    trend: Trend | None = None  # which arrow to show next to `change`
