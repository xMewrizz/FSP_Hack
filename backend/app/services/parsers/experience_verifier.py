from __future__ import annotations

import re
import uuid
from datetime import date

from app.services.parsers.careerist_parser import CareeristParser
from app.services.parsers.date_utils import parse_date_span, parse_experience_duration_text
from app.services.parsers.habr_career_parser import HabrCareerParser
from app.services.parsers.profi_ru_parser import ProfiRuParser
from app.services.parsers.schemas import (
    CandidateSanitizedAuditView,
    ExperienceAuditStatus,
    ExperienceVerificationAudit,
    ParsedExternalProfile,
)


class ExperienceVerifier:
    """
    Сервис верификации опыта и сравнения с внешними источниками (B-41).
    
    Выявляет признаки накрутки опыта («возможно крутит опыт»).
    
    СТРОГАЯ ЗАЩИТА ПРИВАТНОСТИ КАНДИДАТА:
    Сам кандидат НЕ видит статус «возможно крутит опыт» и внутренние флаги расхождений.
    Аудит и объяснения доступны исключительно авторизованным работодателям и рекрутерам.
    
    ПРАВИЛО ПРОФИ.РУ:
    Само наличие подработки или репетиторства на Профи.ру НЕ трактуется как завышение опыта.
    """

    @classmethod
    def verify_candidate_experience(
        cls,
        candidate_id: uuid.UUID,
        declared_grade: str | None = None,
        resume_text: str | None = None,
        candidate_skills: list[str] | None = None,
        external_profiles: list[ParsedExternalProfile] | None = None,
        habr_client_id: str | None = None,
        habr_is_activated: bool = False,
        careerist_is_authorized: bool = False,
    ) -> ExperienceVerificationAudit:
        profiles = external_profiles or []

        # Проверки доступности и правил площадок
        habr_check = HabrCareerParser.check_api_status(
            client_id=habr_client_id,
            is_activated=habr_is_activated,
        )
        careerist_check = CareeristParser.check_access_and_terms(
            is_authorized_employer=careerist_is_authorized,
        )
        profi_check = ProfiRuParser.check_profi_policy()

        # 1. Расчёт заявленного стажа кандидата
        claimed_months, earliest_claimed_year = cls._estimate_claimed_experience(
            resume_text=resume_text,
            declared_grade=declared_grade,
        )

        # 2. Разделение внешних профилей на формальную занятость и подработку
        formal_profiles = [p for p in profiles if not p.is_freelance_or_part_time]
        freelance_profiles = [p for p in profiles if p.is_freelance_or_part_time]

        verified_formal_months = max((p.total_experience_months for p in formal_profiles), default=0)
        freelance_months = max((p.total_experience_months for p in freelance_profiles), default=0)

        # Поиск самого раннего года начала работы в формальных профилях
        earliest_external_year = None
        for p in formal_profiles:
            for w in p.work_periods:
                if w.start_date:
                    year_match = re.search(r"\b(20\d{2}|19\d{2})\b", w.start_date)
                    if year_match:
                        yr = int(year_match.group(1))
                        if earliest_external_year is None or yr < earliest_external_year:
                            earliest_external_year = yr

        flags: list[str] = []
        reasons: list[str] = []
        is_inflated = False
        discrepancy_months = max(0, claimed_months - verified_formal_months)
        ratio = round(claimed_months / max(verified_formal_months, 1), 2) if verified_formal_months > 0 else (float(claimed_months) if claimed_months > 0 else 1.0)

        # 3. Анализ и принятие решения
        if not formal_profiles and not freelance_profiles:
            status = ExperienceAuditStatus.INSUFFICIENT_DATA
            summary = "Внешние профили для сверки стажа не привязаны или не найдены."
            guidance = "Рекомендуется запросить подтверждающие документы или ссылки на профили в ходе интервью."
        elif not formal_profiles and freelance_profiles:
            # Только Профи.ру — подработка не считается накруткой опыта!
            status = ExperienceAuditStatus.NORMAL
            summary = "Найдены сведения о частной практике/репетиторстве на Профи.ру. Формальный трудовой стаж на внешних площадках не найден."
            reasons.append(
                "Подработка на Профи.ру учитывается как подтверждение навыков и практической деятельности. "
                "По правилам платформы, наличие заказов на Профи.ру не является основанием для подозрения в завышении опыта."
            )
            guidance = "Опыт фриланса и репетиторства можно обсудить на техническом интервью как проектный опыт."
        elif claimed_months == 0:
            status = ExperienceAuditStatus.INSUFFICIENT_DATA
            summary = "В резюме не указан стаж, который можно сопоставить с внешними профилями."
            guidance = "Уточните периоды работы у кандидата перед сравнением стажа."
        else:
            # Есть формальные профили (Хабр Карьера, Careerist)
            # Критерий 1: Существенное расхождение в стаже (завышен в 2+ раза при разрыве от 2 лет, либо заявлен Middle/Senior при подтверждённом < 18 мес.)
            inflation_detected = False
            if (
                (ratio >= 2.0 and discrepancy_months >= 24)
                or (claimed_months >= 36 and verified_formal_months < 18 and discrepancy_months >= 24)
            ):
                inflation_detected = True
                reasons.append(
                    f"Заявленный стаж ({claimed_months // 12} г. {claimed_months % 12} мес.) существенно превышает "
                    f"подтверждённый на внешних площадках ({verified_formal_months // 12} г. {verified_formal_months % 12} мес.). "
                    f"Коэффициент расхождения: {ratio}x."
                )

            # Критерий 2: Серьёзный разрыв в датах начала карьеры
            if (
                earliest_claimed_year is not None
                and earliest_external_year is not None
                and earliest_external_year - earliest_claimed_year >= 3
            ):
                inflation_detected = True
                reasons.append(
                    f"Нестыковка года старта карьеры: в резюме указан опыт с {earliest_claimed_year} года, "
                    f"тогда как первая подтверждённая запись на внешних ресурсах появилась только в {earliest_external_year} году."
                )

            if inflation_detected:
                status = ExperienceAuditStatus.POSSIBLY_INFLATED
                is_inflated = True
                flags.append("возможно крутит опыт")
                summary = (
                    "Обнаружено критическое расхождение между заявленным стажем и записями в профессиональных источниках "
                    "(Хабр Карьера / Careerist). Кандидату присвоен внутренний статус «возможно крутит опыт»."
                )
                guidance = (
                    "Обратите внимание на трудовую биографию на интервью. Проверьте реальные даты начала коммерческого опыта. "
                    "Внимание: статус скрыт от кандидата согласно политике сервиса."
                )
            else:
                status = ExperienceAuditStatus.NORMAL
                summary = "Заявленный опыт согласуется с записями в профессиональных профилях."
                reasons.append("Расхождений между резюме и внешними источниками не зафиксировано.")
                guidance = "Трудовая история подтверждена внешними источниками."

            if freelance_profiles:
                reasons.append(
                    "Дополнительно подтверждена активность на Профи.ру (частные заказы/репетиторство). "
                    "Подработка не снижает оценку достоверности кандидата."
                )

        return ExperienceVerificationAudit(
            candidate_id=candidate_id,
            status=status,
            is_flagged_for_inflation=is_inflated,
            claimed_experience_months=claimed_months,
            verified_formal_experience_months=verified_formal_months,
            freelance_experience_months=freelance_months,
            discrepancy_months=discrepancy_months,
            discrepancy_ratio=ratio,
            flags=flags,
            reasons=reasons,
            external_profiles=profiles,
            habr_check=habr_check,
            careerist_check=careerist_check,
            profi_check=profi_check,
            audit_summary=summary,
            employer_guidance=guidance,
            visible_to_candidate=False,
        )

    @classmethod
    def get_candidate_view(cls, audit: ExperienceVerificationAudit) -> CandidateSanitizedAuditView:
        """
        Возвращает очищенное представление аудита для соискателя.
        СТРОГО ИСКЛЮЧАЕТ:
        - Статус 'возможно крутит опыт'
        - Флаги подозрения и коэффициенты расхождения
        - Внутренние комментарии работодателю
        """
        sources = [p.source_name for p in audit.external_profiles]
        return CandidateSanitizedAuditView(
            candidate_id=audit.candidate_id,
            has_external_data=bool(audit.external_profiles),
            sources_connected=sources,
            summary="Профиль сопоставлен с открытыми источниками.",
        )

    @classmethod
    def get_employer_view(cls, audit: ExperienceVerificationAudit) -> ExperienceVerificationAudit:
        """
        Возвращает полный детальный аудит для авторизованного работодателя.
        """
        return audit

    @classmethod
    def _estimate_claimed_experience(
        cls,
        resume_text: str | None,
        declared_grade: str | None,
        current_year: int = 2026,
    ) -> tuple[int, int | None]:
        """
        Оценивает заявленный кандидатом опыт по тексту резюме и заявленному грейду.
        Возвращает: (months, earliest_year).
        """
        if not resume_text:
            return 0, None

        # Поиск явных дат в тексте
        years = [int(y) for y in re.findall(r"\b(20\d{2}|19\d{2})\b", resume_text)]
        valid_work_years = [y for y in years if 1990 <= y <= current_year]

        earliest_year = min(valid_work_years) if valid_work_years else None
        latest_year = max(valid_work_years) if valid_work_years else None

        # Проверяем явное указание стажа вида "Опыт: 5 лет"
        text_dur = parse_experience_duration_text(resume_text)
        if text_dur > 0:
            return text_dur, earliest_year

        is_currently_working = bool(
            re.search(r"(?:настоящее(?:\s+время)?|по\s+н\.?\s*в\.?|н\.?\s*в\.?|сейчас|current|present)", resume_text, re.IGNORECASE)
        )
        if earliest_year and latest_year:
            end_yr = current_year if is_currently_working else latest_year
            calc_months = max(12, (end_yr - earliest_year) * 12)
            return calc_months, earliest_year

        if earliest_year:
            calc_months = max(12, (current_year - earliest_year) * 12)
            return calc_months, earliest_year

        # Заявленный грейд ничего не говорит о продолжительности работы.
        return 0, None
