import uuid
import pytest
from httpx import AsyncClient
from app.models.candidate import CandidateProfile
from conftest import TestingSessionLocal


async def register_verified(client: AsyncClient, email: str, role: str) -> dict[str, str]:
    registered = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "TestPassword123!", "role": role},
    )
    assert registered.status_code == 201
    verified = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": registered.json()["verification_code"]},
    )
    assert verified.status_code == 200
    token = verified.json().get("access_" + "token")
    assert token
    return {"Authorization": "Bearer" + " " + token}


@pytest.mark.asyncio
async def test_team_invitation_shares_private_candidate_review(client: AsyncClient):
    owner = await register_verified(client, "owner@workspace.example.com", "employer")
    teammate = await register_verified(client, "teammate@workspace.example.com", "employer")
    outsider = await register_verified(client, "outsider@workspace.example.com", "employer")
    candidate = await register_verified(client, "public-candidate@workspace.example.com", "candidate")

    company = await client.post(
        "/api/v1/employer/onboarding",
        headers=owner,
        json={"company_name": "Northstar", "contact_person": "Owner"},
    )
    assert company.status_code == 200
    onboarded = await client.post(
        "/api/v1/candidate/onboarding",
        headers=candidate,
        json={
            "first_name": "Public",
            "last_name": "Candidate",
            "specialization": "Backend",
            "declared_grade": "middle",
            "city": "Moscow",
            "agreed_152_fz": True,
            "agreed_publication": True,
            "visibility_public": True,
        },
    )
    assert onboarded.status_code == 200
    candidate_id = onboarded.json()["id"]
    async with TestingSessionLocal() as db:
        profile = await db.get(CandidateProfile, uuid.UUID(candidate_id))
        assert profile is not None
        profile.verified_grade = "middle"
        profile.verified_specialization = "Backend"
        await db.commit()

    pre_workspace = await client.get(
        f"/api/v1/matching/candidates/{candidate_id}/review",
        headers=owner,
    )
    assert pre_workspace.status_code == 200
    assert pre_workspace.json()["workspace_active"] is False
    unlinked_team = await client.get("/api/v1/employer/team", headers=teammate)
    assert unlinked_team.status_code == 200
    assert unlinked_team.json()["organization_id"] is None

    invitation = await client.post(
        "/api/v1/employer/team/invitations",
        headers=owner,
        json={"email": "teammate@workspace.example.com"},
    )
    assert invitation.status_code == 200
    invite_id = invitation.json()["invitations"][0]["id"]
    received = await client.get("/api/v1/employer/team", headers=teammate)
    assert received.status_code == 200
    assert received.json()["received_invitations"][0]["id"] == invite_id
    accepted = await client.post(
        f"/api/v1/employer/team/invitations/{invite_id}/accept",
        headers=teammate,
    )
    assert accepted.status_code == 200
    assert accepted.json()["organization_id"] == invitation.json()["organization_id"]
    assert len(accepted.json()["members"]) == 2

    updated = await client.put(
        f"/api/v1/matching/candidates/{candidate_id}/review",
        headers=owner,
        json={
            "notes": "Сильный профиль, уточнить доступность",
            "pipeline_status": "interview",
            "contact_status": "found",
            "background_check_status": "pending",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["notes"] == "Сильный профиль, уточнить доступность"
    shared = await client.get(
        f"/api/v1/matching/candidates/{candidate_id}/review",
        headers=teammate,
    )
    assert shared.status_code == 200
    assert shared.json()["pipeline_status"] == "interview"
    assert shared.json()["background_check_status"] == "pending"

    posted = await client.post(
        f"/api/v1/matching/candidates/{candidate_id}/review/messages",
        headers=teammate,
        json={"body": "Проверю портфолио и вернусь к обсуждению"},
    )
    assert posted.status_code == 200
    assert len(posted.json()["messages"]) == 1
    assert posted.json()["messages"][0]["sender_name"] == "Northstar"
    shared = await client.get(
        f"/api/v1/matching/candidates/{candidate_id}/review",
        headers=owner,
    )
    assert shared.json()["messages"][0]["body"] == "Проверю портфолио и вернусь к обсуждению"

    isolated = await client.get(
        f"/api/v1/matching/candidates/{candidate_id}/review",
        headers=outsider,
    )
    assert isolated.status_code == 200
    assert isolated.json()["notes"] == ""
    assert isolated.json()["messages"] == []
    for pipeline_status in ("onboarding", "mentor_work"):
        progressed = await client.put(
            f"/api/v1/matching/candidates/{candidate_id}/review",
            headers=owner,
            json={"pipeline_status": pipeline_status},
        )
        assert progressed.status_code == 200
        assert progressed.json()["pipeline_status"] == pipeline_status


@pytest.mark.asyncio
async def test_review_requires_published_candidate_and_invitation_owner(client: AsyncClient):
    owner = await register_verified(client, "review-owner@workspace.example.com", "employer")
    member = await register_verified(client, "review-member@workspace.example.com", "employer")
    candidate = await register_verified(client, "private-candidate@workspace.example.com", "candidate")
    await client.post(
        "/api/v1/employer/onboarding",
        headers=owner,
        json={"company_name": "Review team", "contact_person": "Owner"},
    )
    invitation = await client.post(
        "/api/v1/employer/team/invitations",
        headers=owner,
        json={"email": "review-member@workspace.example.com"},
    )
    invitation_id = invitation.json()["invitations"][0]["id"]
    accepted = await client.post(
        f"/api/v1/employer/team/invitations/{invitation_id}/accept",
        headers=member,
    )
    assert accepted.status_code == 200
    forbidden = await client.post(
        f"/api/v1/employer/team/invitations/{invitation_id}/accept",
        headers=candidate,
    )
    assert forbidden.status_code == 403
    non_owner_invite = await client.post(
        "/api/v1/employer/team/invitations",
        headers=member,
        json={"email": "someone@workspace.example.com"},
    )
    assert non_owner_invite.status_code == 403
    onboarded = await client.post(
        "/api/v1/candidate/onboarding",
        headers=candidate,
        json={
            "first_name": "Private",
            "last_name": "Candidate",
            "specialization": "Backend",
            "declared_grade": "middle",
            "city": "Moscow",
            "agreed_152_fz": True,
            "agreed_publication": False,
        },
    )
    assert onboarded.status_code == 200
    hidden = await client.get(
        f"/api/v1/matching/candidates/{onboarded.json()['id']}/review",
        headers=owner,
    )
    assert hidden.status_code == 404
    bad_status = await client.put(
        f"/api/v1/matching/candidates/{onboarded.json()['id']}/review",
        headers=owner,
        json={"pipeline_status": "background_check_complete"},
    )
    assert bad_status.status_code == 422


@pytest.mark.asyncio
async def test_employer_can_invite_team_lead_and_team_lead_can_invite_hr(client: AsyncClient):
    owner = await register_verified(client, "lead-owner@workspace.example.com", "employer")
    lead = await register_verified(client, "team-lead@workspace.example.com", "employer")
    hr = await register_verified(client, "team-hr@workspace.example.com", "employer")

    await client.post(
        "/api/v1/employer/onboarding",
        headers=owner,
        json={"company_name": "Northstar", "contact_person": "Owner"},
    )
    lead_invitation = await client.post(
        "/api/v1/employer/team/invitations",
        headers=owner,
        json={"email": "team-lead@workspace.example.com", "team_role": "team_lead"},
    )
    assert lead_invitation.status_code == 200
    invite_id = lead_invitation.json()["invitations"][0]["id"]
    assert lead_invitation.json()["invitations"][0]["team_role"] == "team_lead"
    accepted = await client.post(
        f"/api/v1/employer/team/invitations/{invite_id}/accept",
        headers=lead,
    )
    assert accepted.status_code == 200
    assert accepted.json()["current_user_can_manage_team"] is True
    assert next(member for member in accepted.json()["members"] if member["email"] == "team-lead@workspace.example.com")["team_role"] == "team_lead"

    hr_invitation = await client.post(
        "/api/v1/employer/team/invitations",
        headers=lead,
        json={"email": "team-hr@workspace.example.com", "team_role": "hr"},
    )
    assert hr_invitation.status_code == 200
    assert hr_invitation.json()["invitations"][0]["team_role"] == "hr"
    hr_invitation_id = hr_invitation.json()["invitations"][0]["id"]
    joined_hr = await client.post(
        f"/api/v1/employer/team/invitations/{hr_invitation_id}/accept",
        headers=hr,
    )
    assert joined_hr.status_code == 200
    assert joined_hr.json()["current_user_can_manage_team"] is False
    forbidden_hr_invite = await client.post(
        "/api/v1/employer/team/invitations",
        headers=hr,
        json={"email": "another-hr@workspace.example.com"},
    )
    assert forbidden_hr_invite.status_code == 403
    vacancy = await client.post(
        "/api/v1/vacancies",
        headers=owner,
        json={
            "title": "Командная вакансия",
            "specialization": "Backend",
            "required_grade": "middle",
            "salary_min": 100000,
            "salary_max": 200000,
            "is_published": False,
        },
    )
    assert vacancy.status_code == 201
    hr_id = next(member["user_id"] for member in joined_hr.json()["members"] if member["email"] == "team-hr@workspace.example.com")
    assigned = await client.put(
        f"/api/v1/vacancies/{vacancy.json()['id']}/permissions",
        headers=lead,
        json={"user_id": hr_id, "can_view": True},
    )
    assert assigned.status_code == 200
    assert next(item for item in assigned.json() if item["user_id"] == hr_id)["can_view"] is True
    hr_lead_invitation = await client.post(
        "/api/v1/employer/team/invitations",
        headers=lead,
        json={"email": "another-lead@workspace.example.com", "team_role": "team_lead"},
    )
    assert hr_lead_invitation.status_code == 403


@pytest.mark.asyncio
async def test_employer_mentor_list_only_includes_public_company_linked_candidates(client: AsyncClient):
    employer = await register_verified(client, "mentor-directory@workspace.example.com", "employer")
    linked = await register_verified(client, "linked-mentor@workspace.example.com", "candidate")
    applicant = await register_verified(client, "applicant-mentor@workspace.example.com", "candidate")
    unrelated = await register_verified(client, "unrelated-mentor@workspace.example.com", "candidate")
    await client.post(
        "/api/v1/employer/onboarding",
        headers=employer,
        json={"company_name": "Northstar", "contact_person": "Owner"},
    )

    candidate_ids = []
    for headers, first_name in ((linked, "Связанный"), (applicant, "Откликнувшийся"), (unrelated, "Другой")):
        onboarded = await client.post(
            "/api/v1/candidate/onboarding",
            headers=headers,
            json={
                "first_name": first_name,
                "last_name": "Ментор",
                "specialization": "Backend",
                "declared_grade": "senior",
                "city": "Москва",
                "skills": ["Python", "PostgreSQL"],
                "agreed_152_fz": True,
                "agreed_publication": True,
                "visibility_public": True,
            },
        )
        assert onboarded.status_code == 200
        candidate_ids.append(onboarded.json()["id"])
        opted_in = await client.put(
            "/api/v1/candidate/profile",
            headers=headers,
            json={"mentor_available": True},
        )
        assert opted_in.status_code == 200
    async with TestingSessionLocal() as db:
        for candidate_id in candidate_ids:
            profile = await db.get(CandidateProfile, uuid.UUID(candidate_id))
            assert profile is not None
            profile.verified_grade = "senior"
            profile.verified_specialization = "Backend"
        await db.commit()

    invitation = await client.post(
        "/api/v1/invitations",
        headers=employer,
        json={
            "candidate_id": candidate_ids[0],
            "offer_description": "Приглашение в команду",
            "contact_method": "Email",
            "salary_min": 150000,
            "salary_max": 200000,
        },
    )
    assert invitation.status_code == 201
    accepted = await client.post(
        f"/api/v1/invitations/{invitation.json()['id']}/accept",
        headers=linked,
    )
    assert accepted.status_code == 200
    vacancy = await client.post(
        "/api/v1/vacancies",
        headers=employer,
        json={
            "title": "Backend",
            "specialization": "Backend",
            "required_grade": "senior",
            "salary_min": 150000,
            "salary_max": 200000,
            "is_published": True,
        },
    )
    assert vacancy.status_code == 201
    application = await client.post(
        f"/api/v1/vacancies/{vacancy.json()['id']}/apply",
        headers=applicant,
        json={"cover_letter": "Интересна вакансия и работа с Python."},
    )
    assert application.status_code == 201

    mentors = await client.get("/api/v1/employer/mentors", headers=employer)
    assert mentors.status_code == 200
    assert {mentor["name"] for mentor in mentors.json()} == {"Связанный Ментор", "Откликнувшийся Ментор"}
    assert all(mentor["company_link"] == "Отклик или принятое приглашение" for mentor in mentors.json())
    assert all("email" not in mentor for mentor in mentors.json())


@pytest.mark.asyncio
async def test_team_workspace_is_created_only_on_explicit_action(client: AsyncClient):
    employer = await register_verified(client, "workspace-owner@workspace.example.com", "employer")
    onboarded = await client.post(
        "/api/v1/employer/onboarding",
        headers=employer,
        json={"company_name": "Northstar", "contact_person": "Owner"},
    )
    assert onboarded.status_code == 200

    before = await client.get("/api/v1/employer/team", headers=employer)
    assert before.status_code == 200
    assert before.json()["organization_id"] is None
    created = await client.post("/api/v1/employer/team/workspace", headers=employer)
    assert created.status_code == 200
    assert created.json()["organization_id"]
    assert created.json()["current_user_is_owner"] is True


@pytest.mark.asyncio
async def test_vacancy_permissions_are_scoped_to_team_and_role(client: AsyncClient):
    owner = await register_verified(client, "vacancy-owner@workspace.example.com", "employer")
    teammate = await register_verified(client, "vacancy-teammate@workspace.example.com", "employer")
    outsider = await register_verified(client, "vacancy-outsider@workspace.example.com", "employer")
    onboarded = await client.post(
        "/api/v1/employer/onboarding",
        headers=owner,
        json={"company_name": "Vacancy team", "contact_person": "Owner"},
    )
    assert onboarded.status_code == 200
    invitation = await client.post(
        "/api/v1/employer/team/invitations",
        headers=owner,
        json={"email": "vacancy-teammate@workspace.example.com"},
    )
    assert invitation.status_code == 200
    invitation_id = invitation.json()["invitations"][0]["id"]
    joined = await client.post(
        f"/api/v1/employer/team/invitations/{invitation_id}/accept",
        headers=teammate,
    )
    assert joined.status_code == 200

    created = await client.post(
        "/api/v1/vacancies",
        headers=owner,
        json={
            "title": "Private team vacancy",
            "specialization": "Backend",
            "required_grade": "middle",
            "salary_min": 100000,
            "salary_max": 200000,
            "is_published": False,
        },
    )
    assert created.status_code == 201
    vacancy_id = created.json()["id"]
    assert (await client.get("/api/v1/vacancies/my", headers=teammate)).json() == []
    assert (await client.get(
        f"/api/v1/vacancies/{vacancy_id}/applications",
        headers=teammate,
    )).status_code == 403

    member_id = next(member["user_id"] for member in joined.json()["members"] if not member["is_owner"])
    granted_view = await client.put(
        f"/api/v1/vacancies/{vacancy_id}/permissions",
        headers=owner,
        json={"user_id": member_id, "can_view": True},
    )
    assert granted_view.status_code == 200
    visible = await client.get("/api/v1/vacancies/my", headers=teammate)
    assert visible.status_code == 200
    assert len(visible.json()) == 1
    assert visible.json()[0]["can_edit"] is False
    assert (await client.get(
        f"/api/v1/vacancies/{vacancy_id}/applications",
        headers=teammate,
    )).status_code == 200
    denied_edit = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=teammate,
        json={"title": "Unauthorized edit"},
    )
    assert denied_edit.status_code == 403

    granted_edit = await client.put(
        f"/api/v1/vacancies/{vacancy_id}/permissions",
        headers=owner,
        json={"user_id": member_id, "can_edit": True},
    )
    assert granted_edit.status_code == 200
    edited = await client.patch(
        f"/api/v1/vacancies/{vacancy_id}",
        headers=teammate,
        json={"title": "Authorized edit"},
    )
    assert edited.status_code == 200
    assert edited.json()["title"] == "Authorized edit"

    revoked = await client.put(
        f"/api/v1/vacancies/{vacancy_id}/permissions",
        headers=owner,
        json={"user_id": member_id},
    )
    assert revoked.status_code == 200
    assert (await client.get("/api/v1/vacancies/my", headers=teammate)).json() == []
    assert (await client.get(
        f"/api/v1/vacancies/{vacancy_id}/applications",
        headers=teammate,
    )).status_code == 403
    assert (await client.get(
        f"/api/v1/vacancies/{vacancy_id}/permissions",
        headers=outsider,
    )).status_code == 403
