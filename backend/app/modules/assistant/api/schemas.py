"""Request and response bodies of the assistant's routes, and the length limits on what users send.

POST /parse takes a ParseRequest and answers the parser's ParseResponse (defined with the use case, in
application/expense_parser.py, with ParsedExpense); POST /chat takes a ChatRequest and answers a ChatResponse
(routes.py). FastAPI validates requests against these models
and describes them in the OpenAPI document. POST /agent's body is AG-UI's own RunAgentInput, checked by
agui_request.read_request, which applies MAX_MESSAGE_LENGTH too.
"""

from pydantic import BaseModel, Field

from app.modules.conversations import ThreadId
from app.modules.assistant.agent.events import ToolCallSummary

# What one chat message may hold (also the web app's text box limit, via the generated contracts).
MAX_MESSAGE_LENGTH = 2000
# The longest note POST /parse reads: notes are a line or two, and every character is sent to the model.
MAX_NOTE_TEXT_LENGTH = 500


# POST /parse's body: the note to read an expense from.
class ParseRequest(BaseModel):
    text: str = Field(
        min_length=1, max_length=MAX_NOTE_TEXT_LENGTH, examples=["Paid 450.50 at Swiggy yesterday via GPay"]
    )


# POST /chat's body: one message, and the conversation it belongs to.
class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1, max_length=MAX_MESSAGE_LENGTH, examples=["I spent 250 on lunch at Subway today, paid by UPI"]
    )
    # Leave it out to start a new conversation; send the thread_id from a reply to continue that one.
    thread_id: ThreadId | None = None


# POST /chat's answer: the whole reply at once, and the tools the agent ran for it.
class ChatResponse(BaseModel):
    # Send this back with the next message to continue the same conversation.
    thread_id: str
    reply: str
    tool_calls: list[ToolCallSummary]
