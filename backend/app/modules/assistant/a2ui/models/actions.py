"""What a Button does when clicked: an event sent back to the agent, or a function the browser runs itself
(the spec's oneOf). The functions SpendWise's insights catalog declares, and their arguments (D209).

Part of the assistant's A2UI models (presentation layer); basic.py's Button uses Action. The classes are Pydantic
models, so they're described in `#` comments: a docstring would become part of their JSON schema.
"""

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from app.core.months import YearMonth
from app.modules import reports
from app.modules.assistant.a2ui.models.base import (
    MAX_USER_MESSAGE_LENGTH,
    A2uiModel,
    ActionName,
    Catalog,
    DataBinding,
)


# What a button sends back when clicked: the action's name and the values it carries.
class EventAction(A2uiModel):
    name: ActionName
    # What to send with the action: bindings are read from the data model at the moment of the click.
    # int before float, or Pydantic would turn an id like 14 into 14.0.
    context: dict[str, DataBinding | str | bool | int | float] | None = None
    # How the click reads in the chat, e.g. "Approve deleting #14" (the spec's userMessage).
    # Capped like UserAction.user_message, so a form can't carry a message its own Save would be refused for.
    user_message: str | None = Field(default=None, max_length=MAX_USER_MESSAGE_LENGTH)


# The functions SpendWise's insights catalog declares for the renderer to run itself (D209). Each one is declared
# rendererOnly and requiresUserActivation: only a person's click runs it, never the agent, and it's never sent to the
# server as an action. The web app runs only these names (its own allow-list).
class ClientFunction(StrEnum):
    # Save one of a month's report downloads (reports.ReportFormat): the renderer fetches it from the reports routes.
    DOWNLOAD_REPORT = "downloadReport"


# downloadReport's arguments: which month, and which file. Only values: the renderer builds the address itself.
class DownloadReportArgs(A2uiModel):
    month: str = Field(pattern=YearMonth.PATTERN)
    format: reports.ReportFormat


# A call of one of the catalog's functions (the spec's FunctionCall): its name ("@call"), its arguments, and the
# catalog that declares it (a surface's default catalog is the basic one, so the call names ours).
class FunctionCall(A2uiModel):
    call: Literal[ClientFunction.DOWNLOAD_REPORT] = Field(validation_alias="@call", serialization_alias="@call")
    args: DownloadReportArgs
    catalog_id: Literal[Catalog.INSIGHTS] = Catalog.INSIGHTS


# A button's action: the spec's oneOf, an event sent back to the agent or a function the renderer runs. Exactly one.
class Action(A2uiModel):
    # When clicked, the renderer sends this event back to the agent as an `action` message.
    event: EventAction | None = None
    # When clicked, the renderer runs this function itself (nothing goes to the agent).
    function_call: FunctionCall | None = None

    @model_validator(mode="after")
    def _one_kind(self) -> Action:
        if (self.event is None) == (self.function_call is None):
            raise ValueError("an action is either an event or a function call")
        return self
