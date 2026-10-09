import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class MentorProfileResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    specialization: str | None
    verified_grade: str | None
    skills: list[str]
    city: str | None


class MentorshipRequestCreate(BaseModel):
    mentor_user_id: uuid.UUID
    skill_focus: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=4000)

    @field_validator("skill_focus", "message", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class NetworkConversationResponse(BaseModel):
    id: uuid.UUID
    other_user_id: uuid.UUID
    other_name: str
    skill_focus: str
    status: str
    can_accept: bool = False
    last_message: str
    updated_at: datetime


class NetworkMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)

    @field_validator("body", mode="before")
    @classmethod
    def trim_body(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class NetworkMessageResponse(BaseModel):
    id: uuid.UUID
    body: str
    created_at: datetime
    is_mine: bool


class NetworkConversationHistoryResponse(BaseModel):
    messages: list[NetworkMessageResponse]
