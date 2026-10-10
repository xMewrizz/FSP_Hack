from __future__ import annotations

from app.models.candidate import CandidateProfile
from app.services.parsers.careerist_parser import CareeristParser
from app.services.parsers.experience_verifier import ExperienceVerifier
from app.services.parsers.habr_career_parser import HabrCareerParser
from app.services.parsers.profi_ru_parser import ProfiRuParser
from app.services.parsers.schemas import (
    ExperienceAuditStatus,
    ExperienceVerificationAudit,
    ParsedExternalProfile,
)


class ExperienceAuditService:
    """
    Координирующий сервис для внешней верификации опыта кандидатов (B-41).
    
    Связывает парсеры Хабр Карьеры, Careerist и Профи.ру с моделью кандидата,
    учитывает согласие на OSINT (152-ФЗ) и формирует аудит для работодателя.
    Кандидат не видит статус «возможно крутит опыт».
    """

    @classmethod
    def audit_candidate(
        cls,
        candidate: CandidateProfile,
        external_profiles: list[ParsedExternalProfile] | None = None,
        habr_client_id: str | None = None,
        habr_is_activated: bool = False,
        careerist_is_authorized: bool = False,
    ) -> ExperienceVerificationAudit:
        # Проверка согласия на OSINT (152-ФЗ)
        if not getattr(candidate, "agreed_osint", False):
            return ExperienceVerificationAudit(
                candidate_id=candidate.id,
                status=ExperienceAuditStatus.INSUFFICIENT_DATA,
                is_flagged_for_inflation=False,
                claimed_experience_months=0,
                verified_formal_experience_months=0,
                freelance_experience_months=0,
                discrepancy_months=0,
                discrepancy_ratio=1.0,
                flags=[],
                reasons=[
                    "Кандидат не предоставил согласие на обогащение профиля открытыми данными (OSINT). "
                    "В соответствии с 152-ФЗ автоматический сбор сведений с внешних площадок отключён."
                ],
                external_profiles=[],
                habr_check=HabrCareerParser.check_api_status(habr_client_id, is_activated=habr_is_activated),
                careerist_check=CareeristParser.check_access_and_terms(careerist_is_authorized),
                profi_check=ProfiRuParser.check_profi_policy(),
                audit_summary="Согласие на OSINT отсутствует. Внешний аудит не проводился.",
                employer_guidance="Запросите ссылки на профессиональные профили или трудовую книжку напрямую у кандидата.",
                visible_to_candidate=False,
            )

        # Если внешние профили уже переданы (из кэша/тестов/интеграции)
        resolved_profiles: list[ParsedExternalProfile] = list(external_profiles or [])

        # Ссылка в резюме не подтверждает владельца профиля и не содержит
        # проверенных сведений о стаже. Используем только реально полученные
        # и сопоставленные внешние профили, переданные интеграцией.

        # Выполняем сравнение опыта
        return ExperienceVerifier.verify_candidate_experience(
            candidate_id=candidate.id,
            declared_grade=candidate.declared_grade,
            resume_text=candidate.resume_text,
            candidate_skills=candidate.skills,
            external_profiles=resolved_profiles,
            habr_client_id=habr_client_id,
            habr_is_activated=habr_is_activated,
            careerist_is_authorized=careerist_is_authorized,
        )


experience_audit_service = ExperienceAuditService()
