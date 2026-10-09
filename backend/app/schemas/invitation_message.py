import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class InvitationMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)

    @field_validator("body", mode="before")
    @classmethod
    def trim_body(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class InvitationMessageResponse(BaseModel):
    id: uuid.UUID
    body: str
    created_at: datetime
    is_mine: bool


class InvitationConversationResponse(BaseModel):
    messages: list[InvitationMessageResponse]
    unread_count: int


class InvitationUnreadCountResponse(BaseModel):
    unread_count: int
    by_invitation: dict[str, int]
