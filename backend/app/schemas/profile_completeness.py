from typing import Literal

from pydantic import BaseModel, Field


class PublicProfileCompleteness(BaseModel):
    score: int = Field(ge=0, le=100)
    status: Literal["insufficient", "partial", "complete"]


class ProfileCompleteness(PublicProfileCompleteness):
    missing: list[str] = Field(default_factory=list)
