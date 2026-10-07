import uuid
from pydantic import BaseModel, Field


class EmployerOnboardingRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    industry: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)
    contact_person: str = Field(..., min_length=2, max_length=100)
    phone: str | None = Field(None, max_length=50)
    city: str | None = Field(None, max_length=100)


class EmployerProfileUpdateRequest(BaseModel):
    company_name: str | None = None
    description: str | None = None
    industry: str | None = None
    website: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    city: str | None = Field(None, max_length=100)
    city: str | None = None


class EmployerProfileResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    company_name: str
    description: str | None = None
    industry: str | None = None
    website: str | None = None
    contact_person: str | None = None
    phone: str | None = None
    city: str | None = None
    onboarding_completed: bool

    model_config = {"from_attributes": True}
