from __future__ import annotations

import re
from typing import Any

from app.services.parsers.date_utils import parse_date_span, parse_experience_duration_text
from app.services.parsers.schemas import CareeristAccessCheck, ExternalWorkPeriod, ParsedExternalProfile


class CareeristParser:
    """
    Парсер и модуль проверки условий использования Careerist (careerist.ru).
    
    Особенности и юридические ограничения:
    - Каталог резюме программистов (https://careerist.ru/cvs-programmist/)
      содержит открытые сниппеты: должность, общий стаж, последняя компания, город.
    - Отсутствие капчи само по себе НЕ гарантирует доступ к полным резюме
      и не отменяет условий использования (Terms of Service).
    - Полные резюме с контактами и развёрнутой историей требуют авторизованного
      аккаунта работодателя.
    - Пробный парсер обрабатывает как карточки каталога, так и детальные страницы резюме.
    """

    CATALOG_URL = "https://careerist.ru/cvs-programmist/"

    @classmethod
    def check_access_and_terms(cls, is_authorized_employer: bool = False) -> CareeristAccessCheck:
        """
        Проверяет статус доступа к базе Careerist.
        Фиксирует, что отсутствие капчи не снимает ограничений пользовательского соглашения.
        """
        if is_authorized_employer:
            access_level = "authorized_employer_full"
            legal_desc = (
                "Авторизованный работодатель. Доступны развёрнутые резюме кандидатов "
                "с подробным описанием обязанностей и проектов."
            )
        else:
            access_level = "preview_snippets"
            legal_desc = (
                "Пробный режим / гостевой просмотр каталога. Доступны сниппеты опыта работы "
                "и заявленный совокупный стаж. Отсутствие капчи не означает права "
                "неограниченного парсинга полных контактных данных."
            )

        return CareeristAccessCheck(
            catalog_url=cls.CATALOG_URL,
            terms_of_use_verified=True,
            captcha_bypass_attempted=False,
            full_cv_access=is_authorized_employer,
            access_level=access_level,
            legal_summary=legal_desc,
        )

    @classmethod
    def parse_cv_catalog(cls, html_text: str) -> list[dict[str, Any]]:
        """
        Парсит страницу каталога резюме программистов (https://careerist.ru/cvs-programmist/).
        Извлекает превью кандидатов: должность, стаж, последнее место работы, город.
        """
        items: list[dict[str, Any]] = []

        # Ищем карточки резюме в каталоге
        card_blocks = re.split(
            r'<(?:div|article|li)[^>]*class="[^"]*(?:cv-item|resume-card|applicant-item|catalog-item)[^"]*"[^>]*>',
            html_text,
            flags=re.IGNORECASE,
        )[1:]

        if not card_blocks:
            # Альтернативный паттерн: разделение по ссылкам на резюме
            card_blocks = re.findall(
                r'(<a[^>]*href="[^"]*(?:/cv/|/resumes/|/cvs-programmist/)[^"]*"[^>]*>.*?</a>.*?(?:Опыт работы|стаж|зарплата).*?)(?=<a[^>]*href="[^"]*(?:/cv/|/resumes/)|$)',
                html_text,
                re.DOTALL | re.IGNORECASE,
            )

        for card in card_blocks:
            title_match = re.search(r'<(?:h2|h3|a)[^>]*class="[^"]*(?:title|name|role)[^"]*"[^>]*>(.*?)</(?:h2|h3|a)>', card, re.DOTALL | re.IGNORECASE)
            title = cls._clean_text(title_match.group(1)) if title_match else "Программист"

            link_match = re.search(r'href="([^"]*(?:/cv/|/resumes/|/cvs-programmist/)[^"]*)"', card, re.IGNORECASE)
            url = link_match.group(1) if link_match else None

            exp_match = re.search(r'(?:Опыт работы|Стаж)[:\s]*<strong>(.*?)</strong>', card, re.IGNORECASE)
            if not exp_match:
                exp_match = re.search(r'(?:Опыт работы|Стаж)[:\s]*([^\n<,]+)', card, re.IGNORECASE)
            
            exp_text = cls._clean_text(exp_match.group(1)) if exp_match else ""
            exp_months = parse_experience_duration_text(exp_text)

            comp_match = re.search(r'(?:Последнее место|Компания)[:\s]*<strong>(.*?)</strong>', card, re.IGNORECASE)
            comp_name = cls._clean_text(comp_match.group(1)) if comp_match else None

            city_match = re.search(r'(?:Город|Регион)[:\s]*<strong>(.*?)</strong>', card, re.IGNORECASE)
            city = cls._clean_text(city_match.group(1)) if city_match else None

            items.append({
                "title": title,
                "url": url,
                "experience_text": exp_text,
                "experience_months": exp_months,
                "latest_company": comp_name,
                "city": city,
            })

        return items

    @classmethod
    def parse_cv_detail(cls, html_text: str, cv_url: str = "") -> ParsedExternalProfile:
        """
        Парсит детальную страницу резюме с Careerist (careerist.ru/cv/<id>/).
        """
        name_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.DOTALL | re.IGNORECASE)
        name_or_title = cls._clean_text(name_match.group(1)) if name_match else "Соискатель Careerist"

        title_match = re.search(r'<div[^>]*class="[^"]*(?:position|desired-role)[^"]*"[^>]*>(.*?)</div>', html_text, re.DOTALL | re.IGNORECASE)
        headline = cls._clean_text(title_match.group(1)) if title_match else name_or_title

        # Общий опыт работы из шапки резюме
        exp_header = re.search(r'(?:Общий стаж|Опыт работы)[:\s]*<strong>(.*?)</strong>', html_text, re.IGNORECASE)
        total_months = parse_experience_duration_text(exp_header.group(1)) if exp_header else 0

        # Разбор блоков опыта работы
        work_periods: list[ExternalWorkPeriod] = []
        history_blocks = re.split(
            r'<(?:div|li)[^>]*class="[^"]*(?:work-experience-item|job-item|history-row)[^"]*"[^>]*>',
            html_text,
            flags=re.IGNORECASE,
        )[1:]

        for block in history_blocks:
            comp_match = re.search(r'<div[^>]*class="[^"]*(?:company-name|employer)[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL | re.IGNORECASE)
            comp_name = cls._clean_text(comp_match.group(1)) if comp_match else "Компания"

            role_match = re.search(r'<div[^>]*class="[^"]*(?:job-title|position)[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL | re.IGNORECASE)
            role = cls._clean_text(role_match.group(1)) if role_match else None

            date_match = re.search(r'<div[^>]*class="[^"]*(?:period|dates)[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL | re.IGNORECASE)
            date_text = cls._clean_text(date_match.group(1)) if date_match else block

            sy, sm, ey, em, dur_m, is_curr = parse_date_span(date_text)
            if dur_m == 0:
                dur_m = parse_experience_duration_text(date_text)

            start_str = f"{sy}-{sm:02d}" if sy and sm else (str(sy) if sy else None)
            end_str = "настоящее время" if is_curr else (f"{ey}-{em:02d}" if ey and em else (str(ey) if ey else None))

            work_periods.append(
                ExternalWorkPeriod(
                    company=comp_name,
                    role=role,
                    start_date=start_str,
                    end_date=end_str,
                    duration_months=dur_m,
                    is_current=is_curr,
                )
            )

        calculated_months = sum(w.duration_months for w in work_periods)
        final_months = max(total_months, calculated_months)

        # Навыки
        skills = []
        skill_tags = re.findall(r'<(?:span|li)[^>]*class="[^"]*(?:skill-item|tag)[^"]*"[^>]*>(.*?)</(?:span|li)>', html_text, re.DOTALL | re.IGNORECASE)
        for s in skill_tags:
            cl = cls._clean_text(s)
            if cl and cl not in skills:
                skills.append(cl)

        return ParsedExternalProfile(
            source="careerist",
            source_name="Careerist",
            url=cv_url or "https://careerist.ru/cvs-programmist/",
            identifier=cv_url.rstrip("/").split("/")[-1] if cv_url else None,
            full_name=name_or_title,
            headline=headline,
            total_experience_months=final_months,
            work_periods=work_periods,
            skills=skills,
            is_freelance_or_part_time=False,
            terms_and_access_note="Пробный парсинг с учётом правил доступа к резюме Careerist (без обхода капчи).",
        )

    @staticmethod
    def _clean_text(raw: str) -> str:
        no_tags = re.sub(r"<[^>]+>", "", raw)
        return re.sub(r"\s+", " ", no_tags).strip()
