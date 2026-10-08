from datetime import datetime
from typing import Any, Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, model_validator


class InvitationCreate(BaseModel):
    candidate_id: uuid.UUID
    need_id: uuid.UUID | None = None
    offer_description: str = Field(..., min_length=10)
    contact_method: str = Field(..., min_length=3)
    salary_min: float = Field(..., gt=0)
    salary_max: float = Field(..., gt=0)
    salary_tax_type: Literal["gross", "net"] = "gross"
    currency: str = "RUB"

    @model_validator(mode="after")
    def validate_salary(self):
        if self.salary_min > self.salary_max:
            raise ValueError("salary_min не может быть больше salary_max")
        return self


class InvitationCandidateAction(BaseModel):
    reply: str | None = None


class CandidateContactsRevealed(BaseModel):
    email: str
    phone: str | None
    telegram: str | None


class InvitationResponse(BaseModel):
    id: uuid.UUID
    employer_id: uuid.UUID
    company_name: str
    candidate_id: uuid.UUID
    candidate_name: str
    need_id: uuid.UUID | None
    need_title: str | None
    offer_description: str
    contact_method: str
    salary_min: float
    salary_max: float
    salary_tax_type: str = "gross"
    currency: str
    status: str
    candidate_reply: str | None
    created_at: datetime
    accepted_at: datetime | None
    candidate_contacts: CandidateContactsRevealed | None = None

    model_config = ConfigDict(from_attributes=True)
