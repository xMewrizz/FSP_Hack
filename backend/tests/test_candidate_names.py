import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
from app.schemas.candidate import CandidateOnboardingRequest, CandidateProfileUpdateRequest


@pytest.mark.parametrize("name", ["Иван", "Анна-Мария", "Anne-Marie", "O'Neil"])
def test_candidate_profile_accepts_normal_names(name: str):
    assert CandidateProfileUpdateRequest(first_name=name).first_name == name


@pytest.mark.parametrize("name", ["asdfgh", "qwerty", "123", "@#$!"])
def test_candidate_profile_rejects_obvious_name_keysmashes(name: str):
    with pytest.raises(ValidationError):
        CandidateProfileUpdateRequest(first_name=name)


def test_candidate_onboarding_rejects_obvious_name_keysmash():
    with pytest.raises(ValidationError):
        CandidateOnboardingRequest(
            agreed_152_fz=True,
            specialization="Backend",
            declared_grade="middle",
            city="Москва",
            first_name="asdfgh",
            last_name="Иванов",
        )


@pytest.mark.parametrize("phone", ["+7 900 123-45-67", "89991234567"])
def test_candidate_profile_accepts_reasonable_phone(phone: str):
    assert CandidateProfileUpdateRequest(phone=phone).phone == phone


@pytest.mark.parametrize("phone", ["телефон", "123", "+1 (2)"])
def test_candidate_profile_rejects_invalid_phone(phone: str):
    with pytest.raises(ValidationError):
        CandidateProfileUpdateRequest(phone=phone)


@pytest.mark.parametrize("email", ["not-an-email", "person@localhost", "person@.com"])
def test_registration_rejects_invalid_email(email: str):
    with pytest.raises(ValidationError):
        RegisterRequest(email=email, password="long-enough")


def test_registration_accepts_normal_email():
    assert str(RegisterRequest(email="person@example.com", password="long-enough").email) == "person@example.com"
