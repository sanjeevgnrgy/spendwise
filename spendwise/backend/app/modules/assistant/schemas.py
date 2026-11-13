from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    # The upper limit matters because every character is sent to Gemini and paid for as tokens.
    prompt: str = Field(min_length=1, max_length=4000)


class AskResponse(BaseModel):
    answer: str
