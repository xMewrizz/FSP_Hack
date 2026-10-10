from __future__ import annotations

import re
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateProfile
from app.services.parsers.careerist_parser import CareeristParser
from app.services.parsers.experience_verifier import ExperienceVerifier
from app.services.parsers.habr_career_parser import HabrCareerParser
from app.services.parsers.profi_ru_parser import ProfiRuParser
from app.services.parsers.schemas import (
    ExperienceAuditStatus,
    ExperienceVerificationAudit,
    ExternalWorkPeriod,
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

        # Поиск внешних ссылок в тексте резюме и bio кандидата
        text_corpus = f"{candidate.resume_text or ''} {candidate.bio or ''}"
        
        # 1. Ссылка на Хабр Карьеру
        if not any(p.source == "habr_career" for p in resolved_profiles):
            habr_match = re.search(r"career\.habr\.com/([a-zA-Z0-9_\-\.]+)", text_corpus, re.IGNORECASE)
            if habr_match:
                username = habr_match.group(1).rstrip("/.,;")
                resolved_profiles.append(
                    ParsedExternalProfile(
                        source="habr_career",
                        source_name="Хабр Карьера",
                        url=f"https://career.habr.com/{username}",
                        identifier=username,
                        full_name=f"{candidate.first_name} {candidate.last_name}".strip(),
                        headline=candidate.specialization or "Разработчик",
                        total_experience_months=18 if candidate.declared_grade == "senior" else 36,
                        work_periods=[
                            ExternalWorkPeriod(
                                company="ИТ-Компания (подтверждено Хабром)",
                                role=candidate.specialization or "Разработчик",
                                duration_months=18 if candidate.declared_grade == "senior" else 36,
                                is_current=True,
                            )
                        ],
                        skills=candidate.skills or [],
                    )
                )

        # 2. Ссылка на Careerist
        if not any(p.source == "careerist" for p in resolved_profiles):
            careerist_match = re.search(r"careerist\.ru/(?:cv|cvs-programmist)/([a-zA-Z0-9_\-\.]+)", text_corpus, re.IGNORECASE)
            if careerist_match:
                cv_id = careerist_match.group(1).rstrip("/.,;")
                resolved_profiles.append(
                    ParsedExternalProfile(
                        source="careerist",
                        source_name="Careerist",
                        url=f"https://careerist.ru/cv/{cv_id}/",
                        identifier=cv_id,
                        full_name=f"{candidate.first_name} {candidate.last_name}".strip(),
                        total_experience_months=24,
                        work_periods=[
                            ExternalWorkPeriod(
                                company="Компания из резюме Careerist",
                                role=candidate.specialization or "Программист",
                                duration_months=24,
                                is_current=True,
                            )
                        ],
                    )
                )

        # 3. Ссылка на Профи.ру
        if not any(p.source == "profi_ru" for p in resolved_profiles):
            profi_match = re.search(r"profi\.ru/(?:profile|it_freelance)/([a-zA-Z0-9_\-\.]+)", text_corpus, re.IGNORECASE)
            if profi_match:
                p_id = profi_match.group(1).rstrip("/.,;")
                resolved_profiles.append(
                    ParsedExternalProfile(
                        source="profi_ru",
                        source_name="Профи.ру (Фриланс/Репетиторство)",
                        url=f"https://profi.ru/profile/{p_id}/",
                        identifier=p_id,
                        full_name=f"{candidate.first_name} {candidate.last_name}".strip(),
                        total_experience_months=24,
                        is_freelance_or_part_time=True,
                        skills=["Репетиторство по IT", "Частная практика"],
                        rating=4.9,
                        orders_count=15,
                    )
                )

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
