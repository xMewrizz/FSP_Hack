from __future__ import annotations

import re
from typing import Any
import httpx

from app.services.parsers.date_utils import parse_date_span, parse_experience_duration_text
from app.services.parsers.schemas import ExternalWorkPeriod, HabrCareerApiCheck, ParsedExternalProfile


class HabrCareerParser:
    """
    Парсер и интеграционный модуль Хабр Карьеры (career.habr.com).
    
    Особенности и ограничения:
    - В профилях содержатся достоверные места работы, должности и сроки.
    - Полнотекстовый поиск по кандидатам ограничен правилами площадки.
    - Для доступа к API требуется регистрация приложения и обязательная активация
      администрацией Хабра (https://career.habr.com/info/legal/api_rules).
    - API отдаёт структурированную историю занятости, стек технологий и грейд.
    """

    RULES_URL = "https://career.habr.com/info/legal/api_rules"

    @classmethod
    def check_api_status(
        cls,
        client_id: str | None = None,
        client_secret: str | None = None,
        is_activated: bool = False,
    ) -> HabrCareerApiCheck:
        """
        Проверяет условия доступа к API Хабр Карьеры согласно правилам:
        https://career.habr.com/info/legal/api_rules
        """
        has_app = bool(client_id and client_id.strip())
        can_access = bool(has_app and is_activated)

        if not has_app:
            status_desc = (
                "Приложение не зарегистрировано. Для использования API Хабр Карьеры "
                "необходимо создать клиентское приложение в настройках Хабра."
            )
        elif not is_activated:
            status_desc = (
                "Приложение зарегистрировано, но ожидает подтверждения и ручной активации "
                "администрацией Хабра. До активации доступ к продакшен-эндпоинтам закрыт."
            )
        else:
            status_desc = (
                "Приложение активно и авторизовано. Доступно извлечение профилей кандидатов, "
                "истории мест работы и квалификаций."
            )

        return HabrCareerApiCheck(
            rules_url=cls.RULES_URL,
            app_registered=has_app,
            habr_activated=is_activated,
            can_access_api=can_access,
            full_search_limited=True,
            returned_fields=[
                "first_name",
                "last_name",
                "title",
                "qualification",
                "companies",
                "positions",
                "experience_dates",
                "duration_months",
                "skills",
            ],
            legal_summary=status_desc,
        )

    @classmethod
    def parse_api_response(cls, payload: dict[str, Any]) -> ParsedExternalProfile:
        """
        Разбирает JSON-ответ официального API Хабр Карьеры.
        """
        user_data = payload.get("user") or payload
        username = user_data.get("username") or user_data.get("alias") or ""
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip() or user_data.get("title", username)
        headline = user_data.get("specialization") or user_data.get("title") or ""
        location = user_data.get("location") or user_data.get("city") or ""

        # Извлечение мест работы
        raw_experiences = user_data.get("experiences") or user_data.get("work_history") or []
        work_periods: list[ExternalWorkPeriod] = []
        total_months = 0

        for exp in raw_experiences:
            comp_name = exp.get("company_name") or exp.get("company", {}).get("title") or "Компания"
            role = exp.get("position") or exp.get("title")
            start_date = exp.get("start_date") or exp.get("date_from")
            end_date = exp.get("end_date") or exp.get("date_to")
            is_current = bool(exp.get("is_current") or not end_date)
            desc = exp.get("description")

            if exp.get("duration_months"):
                duration_m = int(exp["duration_months"])
            else:
                span_text = f"{start_date or ''} - {end_date or 'настоящее время'}"
                _, _, _, _, duration_m, _ = parse_date_span(span_text)

            work_periods.append(
                ExternalWorkPeriod(
                    company=comp_name,
                    role=role,
                    start_date=str(start_date) if start_date else None,
                    end_date=str(end_date) if end_date else ("настоящее время" if is_current else None),
                    duration_months=duration_m,
                    is_current=is_current,
                    description=desc,
                )
            )
            total_months += duration_m

        skills = [str(s) for s in user_data.get("skills") or []]

        return ParsedExternalProfile(
            source="habr_career",
            source_name="Хабр Карьера (API)",
            url=f"https://career.habr.com/{username}" if username else None,
            identifier=username,
            full_name=full_name,
            headline=headline,
            location=location,
            total_experience_months=total_months,
            work_periods=work_periods,
            skills=skills,
            is_freelance_or_part_time=False,
            api_status="api_authorized",
            terms_and_access_note="Получено через API Хабр Карьеры по авторизованному запросу приложения.",
        )

    @classmethod
    def parse_html(cls, html_text: str, profile_url: str = "") -> ParsedExternalProfile:
        """
        Парсит публичную HTML-страницу профиля соискателя на Хабр Карьере (career.habr.com/<user>).
        Извлекает историю работы, названия компаний, должности, даты и навыки.
        """
        # 1. ФИО и заголовок профиля
        name_match = re.search(r'<h1[^>]*class="[^"]*user-name[^"]*"[^>]*>(.*?)</h1>', html_text, re.DOTALL | re.IGNORECASE)
        if not name_match:
            name_match = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html_text, re.IGNORECASE)
        
        full_name = cls._clean_text(name_match.group(1)) if name_match else ""

        title_match = re.search(r'<div[^>]*class="[^"]*user-specialization[^"]*"[^>]*>(.*?)</div>', html_text, re.DOTALL | re.IGNORECASE)
        headline = cls._clean_text(title_match.group(1)) if title_match else ""

        # 2. Блоки мест работы
        work_periods: list[ExternalWorkPeriod] = []
        total_months = 0

        # Ищем карточки опыта работы с помощью разделения по тегу элемента
        raw_splits = re.split(
            r'<(?:div|li)[^>]*class="[^"]*(?:experience-item|work-item|history-item)[^"]*"[^>]*>',
            html_text,
            flags=re.IGNORECASE,
        )[1:]

        exp_blocks = []
        for s in raw_splits:
            chunk = re.split(r'<(?:div|section)[^>]*class="[^"]*(?:profile-section|skills|education)[^"]*"', s, flags=re.IGNORECASE)[0]
            exp_blocks.append(chunk)

        if not exp_blocks:
            # Альтернативный паттерн: поиск секций с компанией и датами
            exp_blocks = re.findall(
                r'((?:<a[^>]*class="[^"]*(?:company_name|link-comp)[^"]*"[^>]*>.*?</a>).*?(?:сентябр|октябр|ноябр|декабр|январ|феврал|март|апрел|май|июн|июл|август|\d{4}).*?)(?=(?:<a[^>]*class="[^"]*(?:company_name|link-comp)|$))',
                html_text,
                re.DOTALL | re.IGNORECASE,
            )

        for block in exp_blocks:
            comp_match = re.search(r'<a[^>]*class="[^"]*(?:company_name|link-comp|company)[^"]*"[^>]*>(.*?)</a>', block, re.DOTALL | re.IGNORECASE)
            if not comp_match:
                comp_match = re.search(r'(?:Компания|Работодатель):\s*<strong>(.*?)</strong>', block, re.DOTALL | re.IGNORECASE)
            
            comp_name = cls._clean_text(comp_match.group(1)) if comp_match else "Компания"

            role_match = re.search(r'<div[^>]*class="[^"]*(?:position|role|title)[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL | re.IGNORECASE)
            role = cls._clean_text(role_match.group(1)) if role_match else None

            # Даты и длительность
            date_match = re.search(r'<div[^>]*class="[^"]*(?:date|period|duration)[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL | re.IGNORECASE)
            date_text = cls._clean_text(date_match.group(1)) if date_match else block

            sy, sm, ey, em, duration_m, is_curr = parse_date_span(date_text)
            if duration_m == 0:
                duration_m = parse_experience_duration_text(date_text)

            start_str = f"{sy}-{sm:02d}" if sy and sm else (str(sy) if sy else None)
            end_str = "настоящее время" if is_curr else (f"{ey}-{em:02d}" if ey and em else (str(ey) if ey else None))

            work_periods.append(
                ExternalWorkPeriod(
                    company=comp_name,
                    role=role,
                    start_date=start_str,
                    end_date=end_str,
                    duration_months=duration_m,
                    is_current=is_curr,
                )
            )
            total_months += duration_m

        # 3. Навыки
        skills = []
        skill_matches = re.findall(
            r'<(?:a|span)[^>]*class="[^"]*(?:skill-tag|preserve-skills|tag)[^"]*"[^>]*>(.*?)</(?:a|span)>',
            html_text,
            re.DOTALL | re.IGNORECASE,
        )
        for s in skill_matches:
            cleaned_skill = cls._clean_text(s)
            if cleaned_skill and len(cleaned_skill) <= 40 and cleaned_skill not in skills:
                skills.append(cleaned_skill)

        username = profile_url.rstrip("/").split("/")[-1] if profile_url else None

        return ParsedExternalProfile(
            source="habr_career",
            source_name="Хабр Карьера (HTML)",
            url=profile_url or (f"https://career.habr.com/{username}" if username else None),
            identifier=username,
            full_name=full_name or "Пользователь Хабр Карьеры",
            headline=headline or None,
            total_experience_months=total_months,
            work_periods=work_periods,
            skills=skills,
            is_freelance_or_part_time=False,
            terms_and_access_note="Извлечено из открытого профиля Хабр Карьеры.",
        )

    @staticmethod
    def _clean_text(raw: str) -> str:
        no_tags = re.sub(r"<[^>]+>", "", raw)
        return re.sub(r"\s+", " ", no_tags).strip()
