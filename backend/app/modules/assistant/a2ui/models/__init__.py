"""A2UI v1.0 messages, and the components SpendWise allows (a subset of the basic catalog, plus its own insights
catalog), as Pydantic models: a declarative copy of the spec's schema.

A2UI describes UI as data: a flat list of components that point at each other by id, starting from the one with
id "root". The browser draws each one with its own trusted components, so the agent never sends HTML or code.

Presentation layer, inside the assistant: base.py (names, limits, ids, the base model), basic.py (the basic
catalog's components), actions.py (what a click does), insights.py (Chart, Stat) and messages.py (createSurface,
action). This package re-exports every name, so callers import from `a2ui.models`.
"""

from app.modules.assistant.a2ui.models.actions import (
    Action,
    ClientFunction,
    DownloadReportArgs,
    EventAction,
    FunctionCall,
)
from app.modules.assistant.a2ui.models.base import (
    A2UI_VERSION,
    MAX_CHART_POINTS,
    MAX_STAT_TEXT_LENGTH,
    MAX_UNIT_LENGTH,
    MAX_USER_MESSAGE_LENGTH,
    ROOT_ID,
    SURFACE_ID_MAX_LENGTH,
    A2uiModel,
    ActionName,
    Align,
    Catalog,
    ChartType,
    ComponentId,
    DataBinding,
    DynamicString,
    Justify,
    SurfaceId,
    Trend,
)
from app.modules.assistant.a2ui.models.basic import (
    Button,
    Card,
    ChoiceOption,
    ChoicePicker,
    Column,
    DateTimeInput,
    Divider,
    List,
    Row,
    Text,
    TextField,
)
from app.modules.assistant.a2ui.models.insights import (
    Chart,
    ChartPoint,
    Stat,
)
from app.modules.assistant.a2ui.models.messages import (
    ActionMessage,
    Component,
    CreateSurface,
    CreateSurfaceMessage,
    UserAction,
)

__all__ = [
    "A2UI_VERSION",
    "MAX_CHART_POINTS",
    "MAX_STAT_TEXT_LENGTH",
    "MAX_UNIT_LENGTH",
    "MAX_USER_MESSAGE_LENGTH",
    "ROOT_ID",
    "SURFACE_ID_MAX_LENGTH",
    "A2uiModel",
    "Action",
    "ActionMessage",
    "ActionName",
    "Align",
    "Button",
    "Card",
    "Catalog",
    "Chart",
    "ChartPoint",
    "ChartType",
    "ChoiceOption",
    "ChoicePicker",
    "ClientFunction",
    "Column",
    "Component",
    "ComponentId",
    "CreateSurface",
    "CreateSurfaceMessage",
    "DataBinding",
    "DateTimeInput",
    "Divider",
    "DownloadReportArgs",
    "DynamicString",
    "EventAction",
    "FunctionCall",
    "Justify",
    "List",
    "Row",
    "Stat",
    "SurfaceId",
    "Text",
    "TextField",
    "Trend",
    "UserAction",
]
