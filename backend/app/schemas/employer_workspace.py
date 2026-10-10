from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, Field


PipelineStatus = Literal[
    "new",
    "contact_search",
    "contacted",
    "screening",
    "interview",
    "offer",
    "onboarding",
    "mentor_work",
    "hired",
    "rejected",
]
ContactSearchStatus = Literal["not_started", "searching", "found", "unavailable"]
BackgroundCheckStatus = Literal["not_started", "pending", "clear", "review", "blocked"]


class CandidateReviewUpdate(BaseModel):
    notes: str | None = Field(None, max_length=12000)
    pipeline_status: PipelineStatus | None = None
    contact_status: ContactSearchStatus | None = None
    background_check_status: BackgroundCheckStatus | None = None


class CandidateReviewMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class CandidateReviewMessageResponse(BaseModel):
    id: uuid.UUID
    sender_user_id: uuid.UUID
    sender_name: str
    body: str
    created_at: datetime


class CandidateReviewResponse(BaseModel):
    candidate_profile_id: uuid.UUID
    workspace_active: bool = True
    notes: str
    pipeline_status: PipelineStatus
    contact_status: ContactSearchStatus
    background_check_status: BackgroundCheckStatus
    updated_at: datetime | None
    messages: list[CandidateReviewMessageResponse]


class EmployerTeamMemberResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    company_name: str
    is_owner: bool
    team_role: Literal["owner", "team_lead", "hr"]


class EmployerTeamInvitationResponse(BaseModel):
    id: uuid.UUID
    invited_email: str
    status: Literal["pending", "accepted", "cancelled"]
    created_at: datetime
    team_role: Literal["team_lead", "hr"] = "hr"


class EmployerTeamResponse(BaseModel):
    current_user_id: uuid.UUID
    organization_id: uuid.UUID | None
    organization_name: str | None
    current_user_is_owner: bool
    current_user_can_manage_team: bool = False
    members: list[EmployerTeamMemberResponse]
    invitations: list[EmployerTeamInvitationResponse]
    received_invitations: list[EmployerTeamInvitationResponse]


class EmployerTeamInvitationCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    team_role: Literal["team_lead", "hr"] = "hr"


class EmployerTeamInvitationCreated(BaseModel):
    id: uuid.UUID
    invited_email: str
    status: Literal["pending"]
    created_at: datetime
